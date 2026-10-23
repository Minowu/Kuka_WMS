import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { getHomePathFromUser } from '@/utils/authSession'
import AdminLayout from './AdminLayout'

/** Chọn layout: Admin vào Desktop Shell, Operator tự động redirect vào đúng màn hình PDA 4.2". */
export default function MainLayout() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = !!user?.access?.is_admin || (user?.roles || []).some((r) => r.name === 'admin')

  if (isAdmin) {
    return <AdminLayout />
  }

  // Operator luôn được định tuyến trực tiếp đến trang PDA chuyên dụng của họ
  return <Navigate to={getHomePathFromUser(user)} replace />
}
