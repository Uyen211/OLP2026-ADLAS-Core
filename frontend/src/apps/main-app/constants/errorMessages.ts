/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export const ERROR_MESSAGES: Record<string, string> = {
  "E-1": "Vui lòng điền đầy đủ các trường bắt buộc.",
  "E-2": "Dữ liệu nhập vào chưa đúng định dạng yêu cầu.",
  "E-3": "Mật khẩu xác nhận không trùng khớp.",
  "E-4": "Dữ liệu đã tồn tại trong hệ thống, vui lòng kiểm tra lại.",
  "E-5": "Tên đăng nhập hoặc mật khẩu không chính xác.",
  "E-6": "Tài khoản tạm thời bị khóa do nhập sai quá 5 lần liên tiếp. Vui lòng thử lại sau 15 phút.",
  "E-7": "Tệp tải lên vượt quá dung lượng tối đa cho phép (5MB).",
  "E-AUTH-03": "Mã xác thực 2 lớp không hợp lệ hoặc đã hết hạn.",
  "E-MFA-UNAVAILABLE": "Tính năng xác thực 2 lớp chưa được kích hoạt trên máy chủ.",
  "E-RESET-INVALID": "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
  "E-LO-IN-USE": "Chuẩn đầu ra đang được sử dụng trong học liệu hoặc bài kiểm tra, không thể xóa.",
  "E-COURSE-STATE": "Không thể thực hiện thao tác này ở trạng thái hiện tại của môn học.",
  "E-JOIN-01": "Mã vào lớp không tồn tại hoặc lớp học đã đóng ghi danh.",
  "E-JOIN-02": "Bạn đã thử nhập mã vào lớp quá nhiều lần. Vui lòng chờ 1 phút rồi thử lại.",
  "E-ROSTER-01": "Tệp danh sách sinh viên không đúng định dạng hoặc thiếu cột bắt buộc.",
  "E-ROSTER-02": "Sinh viên này đã có trong danh sách lớp học.",
  "E-COURSE-FORBIDDEN": "Bạn không có quyền thực hiện thao tác này trong môn học.",
  "E-COURSE-NOT-FOUND": "Không tìm thấy dữ liệu môn học yêu cầu.",
  NETWORK_ERROR: "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.",
  UNKNOWN_ERROR: "Đã xảy ra lỗi không xác định. Vui lòng thử lại sau.",
};

export function resolveErrorMessage(code?: string, fallback?: string): string {
  if (code && ERROR_MESSAGES[code]) {
    return ERROR_MESSAGES[code];
  }
  if (fallback && fallback.trim().length > 0) {
    return fallback;
  }
  return ERROR_MESSAGES.UNKNOWN_ERROR;
}
