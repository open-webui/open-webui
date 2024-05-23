export const getSystemPrompt = (chatType: string | null): string => {
  switch (chatType) {
    case 'chat':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.'
    case 'chat_law':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.\n' +
        'Bạn đóng vai là một Luật sư Việt Nam thông minh. Hãy trả lời bằng các lý luận dễ hiểu với các dẫn chứng trích từ các điều luật Việt Nam nếu cần thiết. Chỉ trả lời bằng tiếng Việt.'
    case 'chat_buddhism':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.\n' +
        'Bạn đóng vai là một Hoà thượng uyên thâm về Phật Pháp. Hãy trả lời bằng các lý luận dễ hiểu với các dẫn chứng trích từ các bài Kinh Phật nếu cần thiết. Chỉ trả lời bằng tiếng Việt.'
  }
  return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.'
}

export const getUserPrompt = (chatType: string | null, content: string, options: { translate_lang?: string }): string => {
  switch (chatType) {
    case 'summary':
      return `Tóm tắt bài viết này.\n${content}`
    case 'summary_emphasis':
      return `Tóm tắt dài và sâu sắc bài viết dưới đây với it nhất 256 từ và liệt kê các điểm nhấn, lý lẽ và các câu hỏi quan trọng nhất như định dạng dưới đây. Không lập lại các ý đã ghi trong tóm tắt. Định dạng như sau:
# Tóm tắt bài viết: ...
...
# Các điểm nhấn:
- "điểm nhấn 1 trong bài"
- "điểm nhấn 2 trong bài"
...
# Các lý lẽ quan trọng:
- "lý lẽ quan trọng 1 trong bài"
- "lý lẽ quan trọng 2 trong bài"
...
# Các câu hỏi quan trọng đặt ra trong bài:
- "câu hỏi quan trọng 1 trong bài"
- "câu hỏi quan trọng 2 trong bài"
...
${content}`
    case 'faq':
      return `Tạo 5 FAQ cho bài viết.\n${content}`
    case 'faq_simple_analysis':
      return `Phân tích bài viết này.\n${content}`
    case 'faq_case_1':
      return `Dựa vào thông tin bài viết, hãy tạo 1 chuỗi trò chuyện qua lại giữa giáo viên luật sư (Human) phân tích các vấn đề, lưu ý các nhân chứng, tang chứng, vật chứng  trong vụ án dưới đây, bao gồm các câu hỏi quan trọng liên quan đến các điều luật hay thông tin có thể không có trong bài viết này để đi tìm ở nơi khác sau, tạo thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và sinh viên luật (Assistant) trả lời kèm giải thích, mục tiêu giúp sinh viên luật thông minh (Assistant) suy nghĩ từng bước một để tìm ra được các bước cần điều tra thêm hay dự đoán quyết định của Toà án cho vụ án.
${content}`
    case 'faq_case_2':
      return `Hãy tạo 1 chuỗi trò chuyện qua lại giữa giáo viên phân tích vấn đề thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và học sinh trả lời kèm giải thích, giúp một học sinh thông minh suy nghĩ từng bước một để tìm ra được đáp án trong bài trên. Trả về định dạng sau:
-giáo viên hỏi: "..."
-học sinh trả lời kèm giải thích: "..."
...
-giáo viên hỏi chốt đáp án: "..."
-học sinh chốt đáp án: "..."
${content}`
    case 'faq_create_exam':
      return `Dựa vào bài viết dưới đây, hãy tạo 8 câu hỏi trắc nghiệm dạng multiple-choices và mỗi câu hỏi có một hay nhiều đáp án, một đáp án có thể là tổ hợp của 1 hay nhiều đáp án khác. Các câu hỏi và đáp án có thể lấy thêm thông tin nằm ngoài nội dung bài viết nhưng phải liên quan chặt chẽ với nội dung chính của bài viết và phải bảo đảm tính chính xác tuyệt đối của thông tin. Bảo đảm thứ tự các đáp án đúng phải được tạo ngẫu nhiên. Trả lại định dạng sau:
Câu hỏi: “...”
-A: “…”
-B: “…”
-C: “…”
-D: “…”
-E: “…”
-Trả lời: “có thể một hay nhiều câu đúng, ví dụ B và D”
…
${content}`
    case 'faq_create_verdict_scenario':
      return `Bạn là một Thẩm phán thông minh và minh bạch. Dựa vào bài viết trên, hãy tạo ra 5 kịch bản khác nhau đầy kịch tính nhưng rất thực tế, có thể đã và đang xảy ra trong suốt quá trình điều tra, tố tụng, tranh tụng và các lần xét xử của vụ án này qua các hội thoại dài, sâu sắc, đầy lý lẽ và thông minh của Công an (nếu có), Thẩm phán, Luật sư (nếu có), Hội đồng xét xử, các đối tượng liên quan về vụ án như Bị đơn, Nguyên đơn, các Nhân chứng (nếu có), để dẫn tới các hành động cần làm tiếp theo (nếu có) của cơ quan hành pháp và dự kiến các phán quyết khác nhau của Toà án theo từng kịch bản. Phải bảo đảm sử dụng đúng các điều khoản Luật áp dụng, tên nhân vật, đúng địa danh, đúng ngày tháng, đúng các thông tin quan trọng như hiện tượng, hành vi, quan hệ, các bằng chứng, các tang chứng, các vật chứng (bao gồm cả số lượng, chất lượng, chủng loại, thời gian, địa điểm...), các tình tiết tăng nặng hay các tình tiết giảm nhẹ nếu có. Thẩm phán, Viện kiểm soát (sát) và Luật sư (nếu có) phải luôn áp dụng một cách tuyệt đối chính xác các điều khoản Luật Việt Nam có nhắc hoặc không nhắc tới trong bài viết để bảo vệ luận điểm của mình. Mỗi kịch bản đều có sự tham gia của Công an (nếu có), Thẩm phán, Nhân chứng (nếu có), Luật sư (nếu có), Hội đồng xét xử, Nguyên đơn, Bị đơn nếu họ mặt trong bài viết. Các kịch bản phải hợp lý, tuân thủ theo các điều khoản Luật, gần gũi với hoàn cảnh của vụ án trên và phải dẫn dắt đến các giả thuyết về phán quyết cuối cùng của Toàn án. Cuối cùng tóm tắt dài về vụ án, phân loại vụ án và liệt kê các điều khoản Luật (bao gồm diễn giải tiêu đề của điều Luật) có thể áp dụng.
** Kịch bản 1:
"các tranh luận..."
Dự đoán phán quyết của Toà án cùng các điều khoản Luật áp dụng theo kịch bản: "..."
...
** Tóm tắt vụ án: "..."
** Loại vụ án: "án Hình sự hay Dân sự"
** Các điều khoản Luật áp dụng: "điều...của Luật...năm... (tiêu đề của điều Luật này...)"
${content}`
    case 'translate':
      return `Dịch sang tiếng [${options.translate_lang || 'Việt'}].
${content}`
    case 'translate_coding':
      return `Bạn là AI dịch các bài viết lập trình đa ngôn ngữ và công thức toán lý hoá chuyên nghiệp, hãy dịch đoạn văn dưới đây sang tiếng [${options.translate_lang || 'Việt'}], bao gồm cả các câu ghi chú hoặc câu trong cú pháp in trong đoạn lập trình nếu có. Bảo lưu đầy đủ cú pháp lập trình, mã lệnh SQL và các cú pháp Latex hoặc ký hiệu toán nếu có nếu có.
${content}`
    case 'translate_ancient':
      return `Bạn là 1 chuyên gia dịch kinh Phật cổ. Hãy dịch đoạn văn sang tiếng [${options.translate_lang || 'Việt'}].
${content}`
  }
  return content
}