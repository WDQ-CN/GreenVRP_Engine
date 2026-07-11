import { KeyRound, Moon, Sun } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';
import { useEffect, useState } from 'react';

export function TopBar() {
  const { isAuthenticated, clearApiKey } = useAuthStore();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [dark]);

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <h1 className="ml-12 text-lg font-semibold lg:ml-0">GreenVRP Engine</h1>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setDark(!dark)}
          aria-label="切换主题"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button
          variant={isAuthenticated ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            if (isAuthenticated) {
              clearApiKey();
            } else {
              window.dispatchEvent(new CustomEvent('greenvrp:open-auth'));
            }
          }}
          className="gap-2"
        >
          <KeyRound className="h-4 w-4" />
          {isAuthenticated ? '退出认证' : '设置 API Key'}
        </Button>
      </div>
    </header>
  );
}
