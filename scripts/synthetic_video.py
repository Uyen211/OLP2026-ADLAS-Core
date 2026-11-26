# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure-Python synthetic H.264/MP4 test video generator using Pillow (no ffmpeg required)."""

import os
import struct
from PIL import Image, ImageDraw, ImageFont


class _BitWriter:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.cur = 0
        self.bits = 0

    def write_bits(self, val: int, n: int) -> None:
        for i in range(n - 1, -1, -1):
            self.cur = (self.cur << 1) | ((val >> i) & 1)
            self.bits += 1
            if self.bits == 8:
                self.buf.append(self.cur)
                self.cur = 0
                self.bits = 0

    def write_ue(self, val: int) -> None:
        val += 1
        n = val.bit_length() - 1
        self.write_bits(0, n)
        self.write_bits(val, n + 1)

    def write_se(self, val: int) -> None:
        mapped = 2 * val - 1 if val > 0 else -2 * val
        self.write_ue(mapped)

    def align_zero(self) -> None:
        if self.bits > 0:
            self.write_bits(0, 8 - self.bits)

    def rbsp_trailing_bits(self) -> None:
        self.write_bits(1, 1)
        self.align_zero()


def _ebsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros >= 2 and b <= 3:
            out.append(3)
            zeros = 0
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
    return bytes(out)


def _make_sps(width_mbs: int, height_mbs: int) -> bytes:
    bw = _BitWriter()
    bw.write_bits(0x67, 8)  # NAL header: IDR/SPS (type 7)
    bw.write_bits(66, 8)    # profile_idc = 66 (Baseline)
    bw.write_bits(0xC0, 8)  # constraint_set0_flag=1, constraint_set1_flag=1
    bw.write_bits(30, 8)    # level_idc = 30 (3.0)
    bw.write_ue(0)          # seq_parameter_set_id
    bw.write_ue(0)          # log2_max_frame_num_minus4
    bw.write_ue(0)          # pic_order_cnt_type
    bw.write_ue(0)          # log2_max_pic_order_cnt_lsb_minus4
    bw.write_ue(0)          # max_num_ref_frames
    bw.write_bits(0, 1)     # gaps_in_frame_num_value_allowed_flag
    bw.write_ue(width_mbs - 1)
    bw.write_ue(height_mbs - 1)
    bw.write_bits(1, 1)     # frame_mbs_only_flag
    bw.write_bits(0, 1)     # direct_8x8_inference_flag
    bw.write_bits(0, 1)     # frame_cropping_flag
    bw.write_bits(0, 1)     # vui_parameters_present_flag
    bw.rbsp_trailing_bits()
    return _ebsp(bytes(bw.buf))


def _make_pps() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0x68, 8)  # NAL header: PPS (type 8)
    bw.write_ue(0)          # pic_parameter_set_id
    bw.write_ue(0)          # seq_parameter_set_id
    bw.write_bits(0, 1)     # entropy_coding_mode_flag (CAVLC)
    bw.write_bits(0, 1)     # bottom_field_pic_order_in_frame_present_flag
    bw.write_ue(0)          # num_slice_groups_minus1
    bw.write_ue(0)          # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)          # num_ref_idx_l1_default_active_minus1
    bw.write_bits(0, 1)     # weighted_pred_flag
    bw.write_bits(0, 2)     # weighted_bipred_idc
    bw.write_se(0)          # pic_init_qp_minus26
    bw.write_se(0)          # pic_init_qs_minus26
    bw.write_se(0)          # chroma_qp_index_offset
    bw.write_bits(0, 1)     # deblocking_filter_control_present_flag
    bw.write_bits(0, 1)     # constrained_intra_pred_flag
    bw.write_bits(0, 1)     # redundant_pic_cnt_present_flag
    bw.rbsp_trailing_bits()
    return _ebsp(bytes(bw.buf))


def _rgb_to_yuv420p(img: Image.Image) -> tuple[bytes, bytes, bytes]:
    w, h = img.size
    ycbcr = img.convert("YCbCr")
    raw = ycbcr.tobytes()
    y_plane = bytearray(w * h)
    u_full = bytearray(w * h)
    v_full = bytearray(w * h)
    for i in range(w * h):
        y_plane[i] = max(16, min(235, raw[i * 3]))
        u_full[i] = max(16, min(240, raw[i * 3 + 1]))
        v_full[i] = max(16, min(240, raw[i * 3 + 2]))

    u_plane = bytearray((w // 2) * (h // 2))
    v_plane = bytearray((w // 2) * (h // 2))
    for row in range(0, h, 2):
        for col in range(0, w, 2):
            idx = (row // 2) * (w // 2) + (col // 2)
            p0 = row * w + col
            u_plane[idx] = u_full[p0]
            v_plane[idx] = v_full[p0]
    return bytes(y_plane), bytes(u_plane), bytes(v_plane)


def _make_idr_slice(y: bytes, u: bytes, v: bytes, width_mbs: int, height_mbs: int, idr_pic_id: int) -> bytes:
    bw = _BitWriter()
    bw.write_bits(0x65, 8)       # NAL header: IDR slice (type 5)
    bw.write_ue(0)               # first_mb_in_slice
    bw.write_ue(7)               # slice_type = 7 (all-I slice)
    bw.write_ue(0)               # pic_parameter_set_id
    bw.write_bits(0, 4)          # frame_num (4 bits: log2_max_frame_num_minus4 + 4)
    bw.write_ue(idr_pic_id)      # idr_pic_id
    bw.write_bits(0, 4)          # pic_order_cnt_lsb (4 bits)
    bw.write_bits(0, 1)          # no_output_of_prior_pics_flag
    bw.write_bits(0, 1)          # long_term_reference_flag
    bw.write_se(0)               # slice_qp_delta

    w = width_mbs * 16
    w_uv = width_mbs * 8
    for mb_y in range(height_mbs):
        for mb_x in range(width_mbs):
            bw.write_ue(25)  # I_PCM macroblock
            bw.align_zero()
            # 16x16 Luma
            for r in range(16):
                off = (mb_y * 16 + r) * w + mb_x * 16
                bw.buf.extend(y[off : off + 16])
            # 8x8 Cb
            for r in range(8):
                off = (mb_y * 8 + r) * w_uv + mb_x * 8
                bw.buf.extend(u[off : off + 8])
            # 8x8 Cr
            for r in range(8):
                off = (mb_y * 8 + r) * w_uv + mb_x * 8
                bw.buf.extend(v[off : off + 8])

    bw.rbsp_trailing_bits()
    return _ebsp(bytes(bw.buf))


def _box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), box_type) + payload


def _full_box(box_type: bytes, version: int, flags: int, payload: bytes) -> bytes:
    header = struct.pack(">BB", version, (flags >> 16) & 0xFF) + struct.pack(">H", flags & 0xFFFF)
    return _box(box_type, header + payload)


def generate_synthetic_mp4(
    filepath: str,
    title: str = "ADLAS Interactive Video Demo",
    duration_seconds: int = 45,
    width: int = 512,
    height: int = 288,
) -> None:
    """Generate a valid playable MP4 (H.264 Baseline, 1fps, 16:9) with a live second counter."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    width_mbs = width // 16
    height_mbs = height // 16

    sps = _make_sps(width_mbs, height_mbs)
    pps = _make_pps()

    try:
        font_lg = ImageFont.truetype("arial.ttf", 40)
        font_sm = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_lg = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    samples: list[bytes] = []
    for sec in range(duration_seconds):
        img = Image.new("RGB", (width, height), (18, 36, 74))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, width, 48], fill=(12, 24, 52))
        draw.text((20, 14), title[:44], fill=(210, 225, 255), font=font_sm)

        timer_str = f"00:{sec:02d} / 00:{duration_seconds:02d}"
        draw.text((width // 2 - 105, height // 2 - 24), timer_str, fill=(255, 255, 255), font=font_lg)

        # Progress bar
        bar_w = int((width - 48) * ((sec + 1) / duration_seconds))
        draw.rectangle([24, height - 38, width - 24, height - 22], fill=(40, 65, 115))
        draw.rectangle([24, height - 38, 24 + bar_w, height - 22], fill=(59, 130, 246))

        y, u, v = _rgb_to_yuv420p(img)
        nal = _make_idr_slice(y, u, v, width_mbs, height_mbs, sec % 2)
        samples.append(struct.pack(">I", len(nal)) + nal)

    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2avc1mp41")
    mdat_payload = b"".join(samples)
    mdat = _box(b"mdat", mdat_payload)

    timescale = 1000
    sample_duration = 1000  # 1 fps
    total_duration = duration_seconds * sample_duration

    mvhd = _full_box(
        b"mvhd", 0, 0,
        struct.pack(">IIIIII", 0, 0, timescale, total_duration, 0x00010000, 0x0100)
        + b"\x00" * 10
        + struct.pack(">9I", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000)
        + b"\x00" * 24
        + struct.pack(">I", 2),
    )

    tkhd = _full_box(
        b"tkhd", 0, 3,
        struct.pack(">IIIIII", 0, 0, 1, 0, total_duration, 0)
        + b"\x00" * 8
        + struct.pack(">HHHH", 0, 0, 0, 0)
        + struct.pack(">9I", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000)
        + struct.pack(">II", width << 16, height << 16),
    )

    mdhd = _full_box(
        b"mdhd", 0, 0,
        struct.pack(">IIIIHH", 0, 0, timescale, total_duration, 0x55C4, 0),
    )
    hdlr = _full_box(b"hdlr", 0, 0, b"\x00" * 4 + b"vide" + b"\x00" * 12 + b"VideoHandler\x00")
    vmhd = _full_box(b"vmhd", 0, 1, struct.pack(">HHHH", 0, 0, 0, 0))
    url_box = _full_box(b"url ", 0, 1, b"")
    dref = _full_box(b"dref", 0, 0, struct.pack(">I", 1) + url_box)
    dinf = _box(b"dinf", dref)

    avcc_payload = (
        struct.pack(">BBBBBB", 1, sps[1], sps[2], sps[3], 0xFF, 0xE1)
        + struct.pack(">H", len(sps)) + sps
        + struct.pack(">B", 1)
        + struct.pack(">H", len(pps)) + pps
    )
    avcc = _box(b"avcC", avcc_payload)
    avc1_payload = (
        b"\x00" * 6
        + struct.pack(">HH", 1, 0)
        + struct.pack(">III", 0, 0, 0)
        + struct.pack(">HHII", width, height, 0x00480000, 0x00480000)
        + struct.pack(">IH", 0, 1)
        + b"\x00" * 32
        + struct.pack(">Hh", 0x0018, -1)
        + avcc
    )
    avc1 = _box(b"avc1", avc1_payload)
    stsd = _full_box(b"stsd", 0, 0, struct.pack(">I", 1) + avc1)
    stts = _full_box(b"stts", 0, 0, struct.pack(">III", 1, duration_seconds, sample_duration))
    # All samples reside contiguously in chunk 1
    stsc = _full_box(b"stsc", 0, 0, struct.pack(">IIII", 1, 1, duration_seconds, 1))
    stsz = _full_box(
        b"stsz", 0, 0,
        struct.pack(">II", 0, duration_seconds) + b"".join(struct.pack(">I", len(s)) for s in samples),
    )

    # Calculate stco offsets after building moov template
    stco_placeholder = _full_box(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", 0))
    stbl_pre = _box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)
    minf_pre = _box(b"minf", vmhd + dinf + stbl_pre)
    mdia_pre = _box(b"mdia", mdhd + hdlr + minf_pre)
    trak_pre = _box(b"trak", tkhd + mdia_pre)
    moov_pre = _box(b"moov", mvhd + trak_pre)

    mdat_data_offset = len(ftyp) + len(moov_pre) + 8
    stco = _full_box(b"stco", 0, 0, struct.pack(">II", 1, mdat_data_offset))
    stbl = _box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf = _box(b"minf", vmhd + dinf + stbl)
    mdia = _box(b"mdia", mdhd + hdlr + minf)
    trak = _box(b"trak", tkhd + mdia)
    moov = _box(b"moov", mvhd + trak)

    with open(filepath, "wb") as f:
        f.write(ftyp + moov + mdat)
