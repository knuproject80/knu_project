const MODE_ACTIONS = [
  { key: 'voiceMode', label: '음성안내' },
  { key: 'highContrast', label: '고대비' },
  { key: 'largeFont', label: '확대하기' },
  { key: 'lowScreenMode', label: '낮은화면' },
];

function isModeActive(actionKey, accessibility = {}) {
  return Boolean(accessibility[actionKey]);
}

export default function ModeBar({ accessibility = {}, onAction, className = '' }) {
  return (
    <nav className={`mode-bar ${className}`.trim()} aria-label="화면 이용 모드 선택">
      {MODE_ACTIONS.map((action) => {
        const active = isModeActive(action.key, accessibility);

        return (
          <button
            key={action.key}
            type="button"
            className={`mode-button ${active ? 'active' : ''}`}
            onClick={() => onAction?.(action.key)}
            aria-pressed={active}
          >
            {action.label}
          </button>
        );
      })}
    </nav>
  );
}
