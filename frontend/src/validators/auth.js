import { z } from 'zod'

export const loginSchema = z.object({
  account: z.string().min(1, '请输入账号'),
  password: z.string().min(8, '密码长度至少 8 位'),
  captcha_answer: z.string().min(1, '请输入验证码结果'),
})

export const registerSchema = z
  .object({
    role: z.enum(['student', 'admin']),
    username: z.string().min(3, '用户名至少 3 位'),
    student_id: z.string().optional(),
    phone: z.string().optional(),
    email: z.string().optional(),
    security_question: z.string().min(2, '请输入安全问题'),
    security_answer: z.string().min(2, '请输入安全问题答案'),
    password: z.string().min(8, '密码长度至少 8 位'),
    confirm_password: z.string().min(8, '确认密码长度至少 8 位'),
    captcha_answer: z.string().min(1, '请输入验证码结果'),
  })
  .superRefine((data, ctx) => {
    if (data.role === 'student' && !data.student_id?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['student_id'],
        message: '学生角色必须填写学号',
      })
    }

    if (!data.phone?.trim() && !data.email?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['phone'],
        message: '手机号或邮箱至少填写一项',
      })
    }

    if (data.email?.trim()) {
      const emailCheck = z.string().email().safeParse(data.email.trim())
      if (!emailCheck.success) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['email'],
          message: '邮箱格式不正确',
        })
      }
    }

    if (data.password !== data.confirm_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confirm_password'],
        message: '两次密码输入不一致',
      })
    }
  })

export const resetCodeSchema = z.object({
  account: z.string().min(1, '请输入账号'),
  security_answer: z.string().min(2, '请输入安全问题答案'),
  captcha_answer: z.string().min(1, '请输入验证码结果'),
})

export const resetSchema = z
  .object({
    account: z.string().min(1, '请输入账号'),
    security_answer: z.string().min(2, '请输入安全问题答案'),
    email_code: z.string().min(4, '请输入邮箱验证码'),
    new_password: z.string().min(8, '新密码长度至少 8 位'),
    confirm_password: z.string().min(8, '确认密码长度至少 8 位'),
    captcha_answer: z.string().min(1, '请输入验证码结果'),
  })
  .superRefine((data, ctx) => {
    if (data.new_password !== data.confirm_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['confirm_password'],
        message: '两次密码输入不一致',
      })
    }
  })
