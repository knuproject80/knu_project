const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '완료', '0', 'X'];

function DeleteKeyIcon() {
  return (
    <svg
      className="delete-key-icon"
      viewBox="0 0 64 48"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M22 8H56C58.2 8 60 9.8 60 12V36C60 38.2 58.2 40 56 40H22L4 24L22 8Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M35 18L47 30M47 18L35 30"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Keypad({ onPress }) {
  return (
    <div className="keypad-grid">
      {KEYS.map((key) => {
        const isDone = key === '완료';
        const isDelete = key === 'X';

        return (
          <button
            key={key}
            type="button"
            className={`keypad-button ${isDone || isDelete ? 'small' : ''} ${isDone ? 'done' : ''} ${isDelete ? 'delete-key-button' : ''}`}
            onClick={() => onPress(key)}
            aria-label={isDelete ? '지우기' : undefined}
          >
            {isDelete ? <DeleteKeyIcon /> : key}
          </button>
        );
      })}
    </div>
  );
}
