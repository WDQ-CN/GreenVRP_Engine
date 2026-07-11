import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { logger } from '@/lib/logger';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReturnHome = () => {
    window.location.href = '/';
  };

  override render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen w-full flex-col items-center justify-center gap-6 p-6 text-center">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">页面出现错误</h1>
            <p className="max-w-md text-muted-foreground">
              抱歉，应用渲染时发生了意外错误。请尝试返回首页或刷新页面。
            </p>
            {this.state.error && import.meta.env.DEV && (
              <pre className="mt-4 max-w-xl overflow-auto rounded-md bg-muted p-4 text-left text-xs text-destructive">
                {this.state.error.message}
              </pre>
            )}
          </div>
          <div className="flex gap-3">
            <Button onClick={this.handleReturnHome}>返回首页</Button>
            <Button variant="outline" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
