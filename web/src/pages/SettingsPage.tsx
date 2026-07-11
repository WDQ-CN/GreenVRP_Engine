import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/stores/authStore';
import { useState } from 'react';

export function SettingsPage() {
  const { apiKey, setApiKey, clearApiKey } = useAuthStore();
  const [input, setInput] = useState(apiKey || '');

  const handleSave = () => {
    if (input.trim()) {
      setApiKey(input.trim());
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">设置</h1>
        <p className="text-muted-foreground">管理 API Key 与偏好设置</p>
      </div>

      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>API Key</CardTitle>
          <CardDescription>
            设置后端 GreenVRP API Key 以访问受保护接口
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="请输入 API Key"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSave}>保存</Button>
            <Button variant="outline" onClick={clearApiKey}>
              清除
            </Button>
          </div>
          {apiKey && <p className="text-sm text-green-600">已配置 API Key</p>}
        </CardContent>
      </Card>
    </div>
  );
}
