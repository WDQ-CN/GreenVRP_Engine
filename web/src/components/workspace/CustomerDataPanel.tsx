import { memo, useCallback, useRef, useState } from 'react';
import { Upload, Download, RefreshCcw, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CustomerTable } from './CustomerTable';
import { parseCustomersCsv, customersToCsv } from '@/lib/csv';
import type { Customer } from '@/types';

interface CustomerDataPanelProps {
  customers: Customer[];
  onCustomersChange: (customers: Customer[]) => void;
  onLoadSampleData: () => void;
}

function CustomerDataPanelInner({
  customers,
  onCustomersChange,
  onLoadSampleData,
}: CustomerDataPanelProps) {
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const text = await file.text();
      const { customers: parsed, errors } = parseCustomersCsv(text);

      if (errors.length > 0) {
        setImportErrors(errors);
      } else {
        onCustomersChange(parsed);
        setImportErrors([]);
      }

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [onCustomersChange]
  );

  const handleExport = useCallback(() => {
    const csv = customersToCsv(customers);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'customers.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [customers]);

  const handleClear = useCallback(() => {
    onCustomersChange([]);
    setShowClearDialog(false);
  }, [onCustomersChange]);

  // 将 onLoadSampleData 包装为稳定的引用
  const handleLoadSampleData = useCallback(() => {
    onLoadSampleData();
  }, [onLoadSampleData]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm text-muted-foreground">
          支持 CSV 导入，表头可为中文或英文
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mr-1 h-4 w-4" />
            导入 CSV
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
            aria-label="导入 CSV 文件"
          />
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-1 h-4 w-4" />
            导出 CSV
          </Button>
          <Button variant="outline" size="sm" onClick={handleLoadSampleData}>
            <RefreshCcw className="mr-1 h-4 w-4" />
            加载示例
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowClearDialog(true)}
            disabled={customers.length === 0}
          >
            <Trash2 className="mr-1 h-4 w-4" />
            清空
          </Button>
        </div>
      </div>

      {importErrors.length > 0 && (
        <div
          className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
          aria-live="polite"
        >
          <p className="font-medium">导入错误：</p>
          <ul className="list-inside list-disc">
            {importErrors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <CustomerTable customers={customers} onChange={onCustomersChange} />

      <Dialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认清空</DialogTitle>
            <DialogDescription>
              此操作将删除所有客户数据，无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleClear}>
              确认清空
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export const CustomerDataPanel = memo(CustomerDataPanelInner);
