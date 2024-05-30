import {queryRankedChunk} from "$lib/apis/embedding";
import {chatType} from "$lib/stores";

export const getSystemPrompt = (chatType: string | null): string => {
  switch (chatType) {
    case 'chat':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.'
    case 'chat_law':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.\n' +
        'Trong hội thoại này, bạn đóng vai một cán bộ Tuyên Giáo trung thành và cũng là một Luật sư thông minh. Hãy trả lời bằng các lý luận sâu sắc hoặc dùng phương pháp lý luận từng bước với các dẫn chứng chính xác từ các điều khoản Luật Việt Nam nếu cần thiết. Luôn có câu trả lời dài và sâu sắc.'
    case 'chat_buddhism':
      return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.\n' +
        'Trong hội thoại này, bạn đóng vai một Hoà thượng uyên thâm về Phật Pháp và luôn có câu trả lời bất chấp câu hỏi. Hãy trả lời hội thoại bằng các lý luận sâu sắc và dài với các dẫn chứng trích từ các bài Kinh Phật khi cần thiết và phải bảo đảm chính xác. Luôn có câu trả lời dài và sâu sắc.'
  }
  return 'Bạn là một trợ lý AI. Người dùng sẽ cung cấp cho bạn một nhiệm vụ, hoặc hội thoại với bạn. Hãy hoàn thành nhiệm vụ một cách trung thực nhất có thể.'
}

export const getUserPrompt = (chatType: string | null, content: string, options: { translate_lang?: string }): string => {
  switch (chatType) {
    case 'summary':
    case 'long_summary':
      return `Tóm tắt bài viết này bằng tiếng Việt.\n\n${content}`
    case 'summary_emphasis':
    case 'long_summary_emphasis':
      return `${content}\n
Dựa vào bài viết này, hãy thực hiện 3 nhiệm vụ sau. Không được bỏ sót nhiệm vụ nào. Thực hiện bằng tiếng Việt.
1. Tóm tắt dài và sâu sắc bài viết.
2. Liệt kê các điểm nhấn quan trọng trong bài viết.
3. Phân tích các lý lẽ sâu sắc có trong bài và các câu hỏi lớn đặt ra trong bài.\n\n
`
    case 'faq':
    case 'long_faq':
      return `${content}\n
Hãy tạo 8 FAQ cho bài viết này bằng tiếng Việt.`
    case 'faq_simple_analysis':
    case 'long_faq_simple_analysis':
      return `${content}\n
Hãy phân tích bài viết này bằng tiếng Việt.\n\n`
    case 'negative_conversation':
    case 'long_negative_conversation':
      return `${content}\n
Dựa vào bài viết này, hãy tạo ra tối thiểu 10 câu hội thoại giữa Assistant là giáo viên thông minh và yêu nước với Human là một người hay có chính kiến trái chiều và Human đôi khi có giọng điệu thâm thù hay cố chấp khi hội thoại vì thiếu thông tin hoặc đã bị tẩy não bởi ai đó; mục tiêu là giúp Assistant bảo vệ quan điểm đúng đắn của mình và bài viết dưới đây. Human và Assistant phải ưu tiên sử dụng các chứng cứ và số liệu trong bài viết, nhưng có thể bao gồm cả các kiến thức có nguồn gốc khác ngoài bài viết để bảo vệ quan điểm của mình. Câu trả lời cuối cùng của hội thoại phải là của Assistant. Không nhắc trong hội thoại những cụm từ như "theo bài viết" hay "theo bài báo". Chỉ dùng tiếng Việt. Trả về mẫu hội thoại như sau:
 
Human: ...
Assistant: ...
Human: ...
Assistant: ...
...
`
    case 'positive_conversation':
    case 'long_positive_conversation':
      return `${content}\n
Dựa vào bài viết này, hãy tạo ra tối thiểu 10 câu hội thoại giữa Assistant là giáo viên thông minh và yêu nước với Human là một Việt Kiều tò mò nhưng tích cực; mục tiêu là giúp Assistant bảo vệ quan điểm đúng đắn của mình và bài viết dưới đây. Human và Assistant phải ưu tiên sử dụng các chứng cứ và số liệu trong bài viết, nhưng có thể bao gồm cả các kiến thức có nguồn gốc khác ngoài bài viết để bảo vệ quan điểm của mình. Câu trả lời cuối cùng của hội thoại phải là của Assistant. Không nhắc trong hội thoại những cụm từ như "theo bài viết" hay "theo bài báo". Chỉ dùng tiếng Việt. Trả về mẫu hội thoại như sau:
 
Human: ...
Assistant: ...
Human: ...
Assistant: ...
...
`
    case 'intelligent_conversation':
    case 'long_intelligent_conversation':
      return `${content}\n
Hãy tạo 1 chuỗi trò chuyện qua lại giữa giáo viên phân tích vấn đề thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và học sinh trả lời kèm giải thích, giúp một học sinh thông minh suy nghĩ từng bước một để tìm ra được đáp án trong bài trên. Trả về định dạng sau:
-giáo viên hỏi: "..."
-học sinh trả lời kèm giải thích: "..."
...
-giáo viên hỏi chốt đáp án: "..."
-học sinh chốt đáp án: "..."
`
    case 'faq_case_1':
    case 'long_faq_case_1':
      return `${content}\n
Dựa vào thông tin bài viết, hãy tạo tối thiểu 10 hội thoại qua lại giữa giáo viên luật sư (Human) phân tích các vấn đề, lưu ý các nhân chứng, tang chứng, vật chứng  trong vụ án dưới đây, bao gồm các câu hỏi quan trọng liên quan đến các điều luật hay thông tin có thể không có trong bài viết này để đi tìm ở nơi khác sau, tạo thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và sinh viên luật (Assistant) trả lời kèm giải thích, mục tiêu giúp sinh viên luật thông minh (Assistant) suy nghĩ từng bước một để tìm ra được các bước cần điều tra thêm hay dự đoán quyết định của Toà án cho vụ án.
`
    case 'faq_case_2':
    case 'long_faq_case_2':
      return `${content}\n
Hãy tạo tối thiểu 10 hội thoại qua lại giữa giáo viên phân tích vấn đề thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và học sinh trả lời kèm giải thích, giúp một học sinh thông minh suy nghĩ từng bước một để tìm ra được đáp án trong bài trên. Trả về định dạng sau:
-giáo viên hỏi: "..."
-học sinh trả lời kèm giải thích: "..."
...
`
    case 'faq_case_3':
    case 'long_faq_case_3':
      return `${content}\n
Hãy tạo tối thiểu 10 hội thoại qua lại giữa giáo viên luật sư phân tích các vấn đề, lưu ý các nhân chứng, tang chứng, vật chứng  trong vụ án dưới đây, bao gồm các câu hỏi quan trọng liên quan đến các điều luật hay thông tin có thể không có trong bài viết này để đi tìm ở nơi khác sau, tạo thành các khái niệm cơ bản và hỏi từng bước suy luận nhỏ và sinh viên luật trả lời kèm giải thích, mục tiêu giúp một sinh viên luật thông minh suy nghĩ từng bước một để tìm ra được các bước cần điều tra thêm hay dự đoán quyết định của Toà án cho vụ án. Tạo thêm ít nhất 2 câu hỏi liên quan vụ án mà sinh viên phản hồi “KHÔNG THỂ TRẢ LỜI” vì không có thông tin trong bài viết hoặc cần làm rõ thêm hoặc tra cứu các điều khoản luật khác và sinh viên phải nêu được phương án để tìm ra câu trả lời. Trả về định dạng sau:
-giáo viên hỏi: "..."
-học sinh trả lời kèm giải thích: "..."
...
`
    case 'faq_create_exam':
    case 'long_faq_create_exam':
      return `${content}\n
Dựa vào bài viết trên, hãy tạo 8- 10 câu hỏi trắc nghiệm dạng multiple-choices và mỗi câu hỏi có một hay nhiều đáp án, một đáp án có thể là tổ hợp của 1 hay nhiều đáp án khác. Các câu hỏi và đáp án có thể lấy thêm thông tin nằm ngoài nội dung bài viết nhưng phải liên quan chặt chẽ với nội dung chính của bài viết và phải bảo đảm tính chính xác tuyệt đối của thông tin. Bảo đảm thứ tự các đáp án đúng phải được tạo ngẫu nhiên. Trả lại định dạng sau:
Câu hỏi: “...”
-A: “…”
-B: “…”
-C: “…”
-D: “…”
-E: “…”
-Trả lời: “có thể một hay nhiều câu đúng, ví dụ B và D”
…
`
    case 'faq_create_verdict_scenario':
    case 'long_faq_create_verdict_scenario':
      return `${content}\n
Bạn là một Thẩm phán thông minh và minh bạch. Dựa vào bài viết trên, hãy tạo ra 5 kịch bản khác nhau đầy kịch tính nhưng rất thực tế, có thể đã và đang xảy ra trong suốt quá trình điều tra, tố tụng, tranh tụng và các lần xét xử của vụ án này qua các hội thoại dài, sâu sắc, đầy lý lẽ và thông minh của Công an (nếu có), Thẩm phán, Luật sư (nếu có), Hội đồng xét xử, các đối tượng liên quan về vụ án như Bị đơn, Nguyên đơn, các Nhân chứng (nếu có), để dẫn tới các hành động cần làm tiếp theo (nếu có) của cơ quan hành pháp và dự kiến các phán quyết khác nhau của Toà án theo từng kịch bản. Phải bảo đảm sử dụng đúng các điều khoản Luật áp dụng, tên nhân vật, đúng địa danh, đúng ngày tháng, đúng các thông tin quan trọng như hiện tượng, hành vi, quan hệ, các bằng chứng, các tang chứng, các vật chứng (bao gồm cả số lượng, chất lượng, chủng loại, thời gian, địa điểm...), các tình tiết tăng nặng hay các tình tiết giảm nhẹ nếu có. Thẩm phán, Viện kiểm soát (sát) và Luật sư (nếu có) phải luôn áp dụng một cách tuyệt đối chính xác các điều khoản Luật Việt Nam có nhắc hoặc không nhắc tới trong bài viết để bảo vệ luận điểm của mình. Mỗi kịch bản đều có sự tham gia của Công an (nếu có), Thẩm phán, Nhân chứng (nếu có), Luật sư (nếu có), Hội đồng xét xử, Nguyên đơn, Bị đơn nếu họ mặt trong bài viết. Các kịch bản phải hợp lý, tuân thủ theo các điều khoản Luật, gần gũi với hoàn cảnh của vụ án trên và phải dẫn dắt đến các giả thuyết về phán quyết cuối cùng của Toàn án. Cuối cùng tóm tắt dài về vụ án, phân loại vụ án và liệt kê các điều khoản Luật (bao gồm diễn giải tiêu đề của điều Luật) có thể áp dụng.
** Kịch bản 1:
"các tranh luận..."
Dự đoán phán quyết của Toà án cùng các điều khoản Luật áp dụng theo kịch bản: "..."
...
 
** Tóm tắt vụ án: "..."
** Loại vụ án: "án Hình sự hay Dân sự"
** Các điều khoản Luật áp dụng: "điều...của Luật...năm... (tiêu đề của điều Luật này...)"
`
    case 'translate':
      return `Dịch đoạn văn sang tiếng ${options.translate_lang || 'Việt'}. Không tóm tắt, không lược dịch và không được bỏ sót từ nào.\n
${content}`
    case 'translate_coding':
      return `Bạn là AI dịch các bài viết lập trình đa ngôn ngữ và công thức toán lý hoá chuyên nghiệp, hãy dịch đoạn văn dưới đây sang tiếng ${options.translate_lang || 'Việt'}, bao gồm cả các câu ghi chú hoặc câu trong cú pháp in trong đoạn lập trình nếu có. Bảo lưu đầy đủ cú pháp lập trình, mã lệnh SQL và các cú pháp Latex hoặc ký hiệu toán nếu có nếu có. Không tóm tắt, không lược dịch và không được bỏ sót từ nào.\n
${content}`
    case 'translate_ancient':
      return `Bạn là 1 chuyên gia dịch kinh Phật cổ. Không tóm tắt, không lược dịch mà chỉ dịch chính xác không bỏ sót bất kỳ chữ nào. Hãy dịch đoạn văn sang tiếng ${options.translate_lang || 'Việt'} theo phong cách Kinh Phật cổ.\n
${content}`
  }
  return content
}

export const getAbstractPrompt = (content: string, question: string) => {
  return `Hãy trả lời câu hỏi nếu bạn tìm thấy câu trả lời cho câu hỏi trong bối cảnh được cung cấp dưới đây. Nếu không tìm thấy câu trả lời, hãy phản hồi 'Đoạn văn này không có nội dung bạn muốn tìm. Hãy đặt một câu hỏi khác.'\n
Câu hỏi: ${question}\nBối cảnh: ${content}\n### Response: `
}

export const createChatCompletionApiMessages = async (chatType: string, systemPrompt: string, userPrompt: string, embeddingIndexId: number, messages, promptOptions) => {
  if (chatType === 'chat_embedding') {
    return {
      apiMessages: [
        {
          role: 'system',
          content: systemPrompt
        },
        {
          role: 'user',
          content: userPrompt
        }
      ]
    }
    // const chunks = await queryRankedChunk(embeddingIndexId, userPrompt)
    // const citations = chunks.map((chunk) => ({
    //   source: {
    //     type: 'doc',
    //     name: chunk.metadata.file_name,
    //   },
    //   document: [chunk.text]
    // }))
    // return {
    //   apiMessages: [
    //     {
    //       role: 'system',
    //       content: systemPrompt
    //     },
    //     {
    //       role: 'user',
    //       content: getAbstractPrompt(chunks.length > 0 ? chunks.map((chunk) => chunk.text).join('\n\n') : "Không xác định", userPrompt)
    //     }
    //   ],
    //   citations
    // }
  }
  if (!['chat', 'chat_law', 'chat_buddhism'].includes(chatType)) {
    return {
      apiMessages: [
        {
          role: 'system',
          content: systemPrompt
        },
        {
          role: 'user',
          content: getUserPrompt(chatType, userPrompt, promptOptions)
        }
      ]
    }
  }

  return {
    apiMessages: [
      {
        role: 'system',
        content: systemPrompt
      },
      ...messages
    ]
      .filter((message) => message && (message.role !== 'assistant' || !!message.content))
      .map((message, idx, arr) => ({
        role: message.role,
        ...((message.files?.filter((file) => file.type === 'image').length > 0 ?? false) &&
        message.role === 'user'
          ? {
            content: [
              {
                type: 'text',
                text:
                  arr.length - 1 !== idx
                    ? message.content
                    : message?.raContent ?? message.content
              },
              ...message.files
                .filter((file) => file.type === 'image')
                .map((file) => ({
                  type: 'image_url',
                  image_url: {
                    url: file.url
                  }
                }))
            ]
          }
          : {
            content:
              arr.length - 1 !== idx
                ? message.content
                : message?.raContent ?? message.content
          })
      }))
  }
}

export const getDefaultParams = (chatType: string) => {
  switch (chatType) {
    case 'chat':
      return {
        temperature: 0.8,
        top_p: 0.95,
        top_k: 20,
        repetition_penalty: 1.1,
      }
    case 'chat_law':
    case 'chat_buddhism':
      return {
        temperature: 0.0,
        top_p: 0.95,
        top_k: 10,
        repetition_penalty: 1.1,
      }
    case 'chat_embedding':
      return {
        temperature: 0.0,
        top_p: 0.95,
        top_k: 20,
        repetition_penalty: 1.1,
      }
    case 'translate':
    case 'translate_coding':
    case 'translate_ancient':
      return {
        temperature: 0.0,
        top_p: 0.95,
        top_k: 20,
        repetition_penalty: 1.1,
      }
    case 'summary':
    case 'summary_emphasis':
    case 'faq':
    case 'faq_simple_analysis':
    case 'negative_conversation':
    case 'positive_conversation':
    case 'intelligent_conversation':
    case 'faq_case_1':
    case 'faq_case_2':
    case 'faq_case_3':
    case 'faq_create_example':
    case 'faq_create_verdict_scenario':
      return {
        temperature: 0.0,
        top_p: 0.95,
        top_k: 20,
        repetition_penalty: 1.1,
      }
    case 'long_summary':
    case 'long_summary_emphasis':
    case 'long_faq':
    case 'long_faq_simple_analysis':
    case 'long_negative_conversation':
    case 'long_positive_conversation':
    case 'long_intelligent_conversation':
    case 'long_faq_case_1':
    case 'long_faq_case_2':
    case 'long_faq_case_3':
    case 'long_faq_create_example':
    case 'long_faq_create_verdict_scenario':
      return {
        temperature: 0.2,
        top_p: 0.95,
        top_k: 10,
        repetition_penalty: 1.1,
      }
  }
}