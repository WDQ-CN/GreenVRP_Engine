import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/stores/authStore';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, setApiKey } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');

  useEffect(() => {
    const onUnauthorized = () => setOpen(true);
    const onOpenAuth = () => setOpen(true);
    window.addEventListener('greenvrp:unauthorized', onUnauthorized);
    window.addEventListener('greenvrp:open-auth', onOpenAuth);
    return () => {
      window.removeEventListener('greenvrp:unauthorized', onUnauthorized);
      window.removeEventListener('greenvrp:open-auth', onOpenAuth);
    };
  }, []);

  const handleSave = () => {
    if (key.trim()) {
      setApiKey(key.trim());
      setOpen(false);
      setKey('');
    }
  };

  return (
    <>
      {children}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>设置 API Key</DialogTitle>
            <DialogDescription>
              后端接口已启用认证，请输入 GreenVRP API Key 继续使用。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-4">
            <Label htmlFor="auth-key">API Key</Label>
            <Input
              id="auth-key"
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="请输入 API Key"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
              }}
            />
          </div>
          <DialogFooter>
            <Button type="submit" onClick={handleSave} disabled={!key.trim()}>
              保存并继续
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {!isAuthenticated && open === false && (
        <div className="fixed bottom-4 right-4 z-50 rounded-lg border bg-card px-4 py-3 text-sm shadow-lg">
          未设置 API Key，部分功能不可用
        </div>
      )}
    </>
  );
}
