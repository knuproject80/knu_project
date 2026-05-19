const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'X'];

export default function Keypad({ onPress }) {
  return (
    <div className="keypad-grid">
      {KEYS.slice(0, 9).map((key) => (
        <button key={key} type="button" className="keypad-button" onClick={() => onPress(key)}>
          {key}
        </button>
      ))}
      <div className="keypad-spacer" />
      {KEYS.slice(9).map((key) => (
        <button key={key} type="button" className="keypad-button small" onClick={() => onPress(key)}>
          {key}
        </button>
      ))}
    </div>
  );
}
