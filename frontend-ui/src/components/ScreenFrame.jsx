export default function ScreenFrame({ children, className = '', accessibility = {} }) {
  const classes = [
    'screen-frame',
    accessibility.highContrast ? 'high-contrast' : '',
    accessibility.lowScreenMode ? 'low-screen' : '',
    accessibility.largeFont ? 'large-font' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <main className={classes} style={{ '--base-font-size': `${accessibility.fontSize || 16}px` }}>
      <div className="screen-inner">{children}</div>
    </main>
  );
}
