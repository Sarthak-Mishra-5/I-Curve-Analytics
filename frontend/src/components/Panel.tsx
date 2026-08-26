import { ReactNode } from 'react';
import clsx from 'clsx';

interface Props {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  // Default (true) matches every existing call site: content is clipped
  // and internally scrollable, which is correct when the panel sits in a
  // fixed-height track (e.g. the 360px chart grid). Pass `scroll={false}`
  // for a panel in an 'auto'-sized grid/flex track (a ticker strip, a small
  // table) whose content should never be clipped.
  scroll?: boolean;
}

export default function Panel({ title, subtitle, actions, children, className, scroll = true }: Props) {
  return (
    <div
      className={className}
      style={{
        backgroundColor: '#141414',
        border: '1px solid #262626',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        // A flex/grid item's automatic minimum size collapses to 0 once its
        // overflow is anything but 'visible' — left at that default, this
        // wrapper (itself a grid/flex item wherever Panel is placed) could
        // shrink toward zero in an 'auto'-sized track under the slightest
        // pressure (a browser zoom level is enough to tip it) instead of
        // sizing to content. Pin the floor explicitly so `overflow: hidden`
        // above — kept unconditionally so the header's background still
        // respects the rounded corners — can't cause that collapse.
        minHeight: 'min-content',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', backgroundColor: '#1a1a1a', borderBottom: '1px solid #262626' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ color: '#e5e5e5', fontWeight: 'bold', letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '11px' }}>{title}</span>
          {subtitle && <span style={{ color: '#666666', fontSize: '10px' }}>{subtitle}</span>}
        </div>
        {actions}
      </div>
      <div style={{ flex: 1, overflowY: scroll ? 'auto' : 'visible', padding: '8px', minHeight: scroll ? undefined : 'min-content' }}>
        {children}
      </div>
    </div>
  );
}
