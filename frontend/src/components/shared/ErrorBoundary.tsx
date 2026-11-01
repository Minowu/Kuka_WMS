import { Component, ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';
import { logger } from '@/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    logger.error(`React ErrorBoundary caught: ${error.message}`, {
      error_name: error.name,
      error_message: error.message,
      stack: error.stack,
      component_stack: errorInfo.componentStack,
    });
  }

  private handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            backgroundColor: '#f8fafc',
          }}
        >
          <Result
            status="error"
            title="Đã xảy ra sự cố giao diện"
            subTitle={
              this.state.error?.message ||
              'Có lỗi không mong muốn xảy ra trong quá trình hiển thị giao diện.'
            }
            extra={[
              <Button type="primary" key="reload" onClick={this.handleReload}>
                Tải lại trang
              </Button>,
            ]}
          />
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
