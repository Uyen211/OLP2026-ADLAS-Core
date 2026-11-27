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
  "E-9": "Hành vi dán nội dung (Paste) bị vô hiệu hóa trong phòng thi Viva nhằm đảm bảo tính trung thực học thuật.",
  "E-GIT-01": "Không thể kết nối tới kho lưu trữ Git công khai. Vui lòng kiểm tra lại đường dẫn hoặc quyền truy cập.",
  "E-VIVA-01": "Cảnh báo chuyển cửa sổ/tab! Hệ thống đã ghi nhận vi phạm rời phòng thi vào nhật ký giám sát.",
  "E-VIVA-02": "Không tìm thấy phiên vấn đáp Viva cho bài nộp này.",
  "E-VIVA-03": "Phiên vấn đáp Viva đã hoàn tất và được niêm phong.",
  "E-VIVA-04": "Đã hết thời gian làm bài vấn đáp Viva. Hệ thống đã tự động niêm phong biên bản.",
  "E-VIVA-PREPARING": "Hệ thống AI đang hoàn tất phân tích bài nộp để tạo câu hỏi vấn đáp. Vui lòng chờ trong giây lát.",
  "E-ASSESSMENT-02": "Chỉ giảng viên của môn học mới có quyền xem bài nộp, bản tóm tắt và biên bản Viva của sinh viên.",
  "E-SUB-01": "Bài nộp đã quá hạn chót cho phép nộp trễ (Until Date).",
  "E-SUB-02": "Mô tả giải trình sử dụng AI phải từ 20 ký tự trở lên.",
  "E-ASN-01": "Lịch nộp bài không hợp lệ: yêu cầu thời điểm mở nhận bài nhỏ hơn hoặc bằng Hạn nộp (Due Date) và Hạn đóng cổng (Until Date) lớn hơn hoặc bằng Hạn nộp.",
  "E-ASN-02": "Bài tập này chưa đến thời điểm mở nhận bài theo lịch đã cấu hình.",
  "E-ASN-03": "Bạn đã sử dụng hết số lần nộp bài tối đa cho phép của bài tập này.",
  "E-ASN-04": "Không thể xóa bài tập vì đã có bài nộp của sinh viên trong hệ thống.",
  "E-RUB-01": "Tổng điểm tối đa của các tiêu chí trong bảng Rubric phải đạt đúng 10.0 điểm.",
  "E-RUB-02": "Bảng Rubric đã tự động đóng băng do đã có bài nộp của sinh viên, không thể chỉnh sửa.",
  "E-RUB-03": "Chuẩn đầu ra (LO) được chọn không thuộc môn học hiện tại.",
  "E-PLG-01": "Bạn phải tích chọn xác nhận cam kết liêm chính học thuật và khai báo AI hợp lệ trước khi tiếp tục.",
  "E-EXP-01": "Vẫn còn sinh viên chưa đủ điểm thành phần. Vui lòng tích xác nhận xuất bản dự kiến trước khi tải tệp.",
  "E-REP-01": "Chỉ Giảng viên phụ trách lớp học phần hoặc Quản trị viên mới có quyền xuất bảng điểm và báo cáo.",
  "E-REP-02": "Không tìm thấy dữ liệu sổ điểm hoặc lớp học phần để kết xuất báo cáo.",
  "E-VIVA-WORD-COUNT": "Câu trả lời vấn đáp phải đạt tối thiểu 50 từ trước khi gửi.",
  "E-EXAM-03": "Ngân hàng câu hỏi không đủ số lượng câu hỏi hợp lệ theo ma trận đề thi yêu cầu.",
  "E-SEC-01": "Khung giờ mở đề thi phải lớn hơn hoặc bằng thời lượng làm bài quy định.",
  "E-SEC-02": "Mật khẩu phòng thi không chính xác. Vui lòng kiểm tra lại với Giảng viên.",
  "E-SEC-03": "Địa chỉ IP máy trạm không thuộc dải IP phòng máy được phép dự thi.",
  "E-EXAM-CLOSED": "Kỳ thi chưa mở, đã đóng hoặc đã quá thời hạn nộp bài cho phép.",
  "E-REG-01": "Đã quá thời hạn 48 giờ gửi đơn phúc khảo kể từ thời điểm công bố điểm.",
  "E-10": "Mất kết nối mạng! Bài làm vẫn đang được lưu an toàn trên máy của bạn và sẽ tự động đồng bộ khi có mạng.",
  "E-13": "Tài liệu học tập và Gia sư AI đang tạm khóa trong thời gian làm bài thi.",
  "E-EXAM-NOT-FOUND": "Không tìm thấy dữ liệu khảo thí yêu cầu.",
  "E-EXAM-FORBIDDEN": "Bạn không có quyền thực hiện thao tác này trong phân hệ khảo thí.",
  "E-EXAM-STATE": "Không thể thực hiện thao tác này ở trạng thái hiện tại của kỳ thi hoặc bài làm.",
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
