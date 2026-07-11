import { Link, useLocation } from 'react-router-dom';
import { Leaf, Menu, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { navigation } from '@/config/navigation';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { Separator } from '@/components/ui/separator';

export function Sidebar() {
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const grouped = navigation.reduce<Record<string, typeof navigation>>(
    (acc, item) => {
      const group = item.group || '其他';
      acc[group] = acc[group] || [];
      acc[group].push(item);
      return acc;
    },
    {}
  );

  const navContent = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-2 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Leaf className="h-5 w-5" />
        </div>
        <span className="text-lg font-bold tracking-tight">GreenVRP</span>
      </div>
      <Separator />
      <nav className="flex-1 space-y-6 overflow-auto p-4">
        {Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            <p className="mb-2 px-2 text-xs font-semibold text-muted-foreground">
              {group}
            </p>
            <ul className="space-y-1">
              {items.map((item) => {
                const Icon = item.icon;
                const active =
                  item.path === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.path);
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      onClick={() => setMobileOpen(false)}
                      aria-current={active ? 'page' : undefined}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        active
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <div className="fixed left-4 top-4 z-40 lg:hidden">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="切换菜单"
          aria-expanded={mobileOpen}
          aria-controls="mobile-sidebar"
        >
          {mobileOpen ? (
            <X className="h-4 w-4" />
          ) : (
            <Menu className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Desktop sidebar */}
      <aside className="hidden w-64 border-r bg-card lg:block">
        {navContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside
            id="mobile-sidebar"
            className="absolute left-0 top-0 h-full w-64 bg-card shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-label="侧边导航"
          >
            {navContent}
          </aside>
        </div>
      )}
    </>
  );
}
