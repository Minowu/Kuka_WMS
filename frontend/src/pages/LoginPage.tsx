import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/useAuthStore'
import {
  UserOutlined,
  LockOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from '@ant-design/icons'
import { loginSchema, LoginRequest } from '@/types/auth'
import { useLogin } from '@/hooks/useAuth'

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { mutate: login, isPending, error } = useLogin()
  const queryClient = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors, isSubmitting }, }
    = useForm<LoginRequest>({
      resolver: zodResolver(loginSchema),
      defaultValues: { username: '', password: '' },
    })

  useEffect(() => {
    const { isAuthenticated } = useAuthStore.getState()
    if (isAuthenticated) return
    reset({ username: '', password: '' })
    queryClient.removeQueries({ queryKey: ['warehouse'] })
  }, [queryClient, reset])

  const Login = (data: LoginRequest) => {
    login(data)
  }

  return (
    <div className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-linear-to-br from-slate-900 via-slate-800 to-slate-950">
      {/* Subtle KUKA orange ambient glow */}
      <div className="pointer-events-none absolute -top-32 -left-32 z-10 h-96 w-96 rounded-full bg-brand-primary/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-32 -bottom-32 z-10 h-96 w-96 rounded-full bg-tech-accent/10 blur-3xl" />

      {/* Industrial Pattern Overlay */}
      <div className="bg-industrial-pattern pointer-events-none absolute inset-0 z-20 opacity-40" />

      <div className="relative z-30 w-full max-w-[420px] px-4 md:max-w-[90%] lg:max-w-[420px]">
        <div className="rounded-[12px] border border-slate-700/40 bg-panel px-6 py-8 shadow-2xl sm:px-9 sm:pt-10 sm:pb-7">
          {/* KUKA WMS Brand Logo */}
          <div className="mb-5 flex items-center justify-center gap-2.5 select-none">
            <span className="text-brand-primary text-3xl font-black tracking-wider sm:text-4xl">
              KUKA
            </span>
            <span className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs font-bold tracking-widest text-slate-200">
              WMS
            </span>
          </div>

          <h1 className="mb-1 text-center text-2xl font-bold text-brand-dark sm:text-[26px]">
            Đăng nhập
          </h1>
          <p className="mb-8 text-center text-sm text-gray-500">
            Chào mừng đến hệ thống quản lý kho & điều phối AMR
          </p>

          {error && (
            <div className="mb-5 text-sm text-red-500 bg-red-50 border border-red-200 rounded-lg p-3 text-center font-medium">
              Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản và mật khẩu.
            </div>
          )}

          <form
            className="space-y-5"
            onSubmit={handleSubmit(Login)}
          >
            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-sm font-semibold text-gray-800">
                Tài khoản:
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 text-gray-400 flex items-center pointer-events-none">
                  <UserOutlined />
                </span>
                <input
                  id="username"
                  type="text"
                  placeholder="Nhập tài khoản"
                  disabled={isPending || isSubmitting}
                  {...register('username')}
                  className={`h-11 w-full rounded-lg border bg-panel pl-10 pr-3 text-sm outline-none transition-all placeholder:text-stripe-ink-mute hover:border-brand-primary focus:border-brand-primary focus:ring-2 focus:ring-tech-accent/25 disabled:cursor-not-allowed disabled:bg-panel-soft ${errors.username
                    ? 'border-stripe-error focus:border-stripe-error focus:ring-stripe-error/15'
                    : 'border-stripe-hairline'
                    }`}
                />
              </div>
              {errors.username && (
                <span className="text-xs text-red-500">{errors.username.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-sm font-semibold text-gray-800">
                Mật khẩu:
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 text-gray-400 flex items-center pointer-events-none">
                  <LockOutlined />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Nhập mật khẩu"
                  disabled={isPending || isSubmitting}
                  {...register('password')}
                  className={`h-11 w-full rounded-lg border bg-panel pl-10 pr-10 text-sm outline-none transition-all placeholder:text-stripe-ink-mute hover:border-brand-primary focus:border-brand-primary focus:ring-2 focus:ring-tech-accent/25 disabled:cursor-not-allowed disabled:bg-panel-soft ${errors.password
                    ? 'border-stripe-error focus:border-stripe-error focus:ring-stripe-error/15'
                    : 'border-stripe-hairline'
                    }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  disabled={isPending || isSubmitting}
                  className="absolute right-3.5 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none disabled:cursor-not-allowed"
                >
                  {showPassword ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                </button>
              </div>
              {errors.password && (
                <span className="text-xs text-red-500">{errors.password.message}</span>
              )}
            </div>

            <button
              type="submit"
              className="mt-2 h-[45px] w-full cursor-pointer rounded-lg border-none bg-linear-to-br from-sidebar to-brand-primary text-base font-bold text-white transition-all hover:brightness-112 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:filter-none"
              disabled={isPending || isSubmitting}
            >
              {isPending ? 'Đang đăng nhập...' : 'Đăng nhập'}
            </button>
          </form>

          <div className="mt-[18px] text-center">
            <a
              href="#"
              className="text-[13px] text-brand-primary transition-colors hover:text-brand-dark hover:underline"
            >
              Quên mật khẩu
            </a>
          </div>

          {/* Copyright Footer inside card */}
          <div className="mt-6 border-t border-slate-100 pt-4 text-center select-none">
            <a
              href="http://thadorobot.com"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium tracking-wider text-slate-400 transition-colors hover:text-brand-primary"
              title="Thado Robot Solution"
            >
              © 2026 THADOROBOT
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
