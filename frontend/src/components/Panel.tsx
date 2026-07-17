import { ReactNode } from 'react';
import clsx from 'clsx';

interface Props {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function Panel({ title, subtitle, actions, children, className }: Props) {
  return (
    <div style={{ backgroundColor: '#141414', border: '1px solid #262626', borderRadius: '4px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', backgroundColor: '#1a1a1a', borderBottom: '1px solid #262626' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ color: '#e5e5e5', fontWeight: 'bold', letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '11px' }}>{title}</span>
          {subtitle && <span style={{ color: '#666666', fontSize: '10px' }}>{subtitle}</span>}
        </div>
        {actions}
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>{children}</div>
    </div>
  );
}
