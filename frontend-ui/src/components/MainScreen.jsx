import { ACCESSIBILITY_ACTIONS } from '../data/options';

function chunkButtons(items, perRow = 3) {
  const rows = [];
  for (let i = 0; i < items.length; i += perRow) {
    rows.push(items.slice(i, i + perRow));
  }
  return rows;
}

function getAccessibilityActiveState(actionKey, accessibility = {}) {
  switch (actionKey) {
    case 'highContrast':
      return accessibility.highContrast;
    case 'largeFont':
      return accessibility.largeFont;
    case 'lowScreenMode':
      return accessibility.lowScreenMode;
    case 'voiceMode':
      return accessibility.voiceMode;
    default:
      return false;
  }
}

export default function MainScreen({
  categories,
  onSelectService,
  onAccessibilityAction,
  accessibility = {},
}) {
  return (
    <>
      <section className="hero-title-box">
        <h2 className="hero-title">원하시는 서비스를 선택해주세요.</h2>
      </section>

      <div className="main-category-list">
        {categories.map((category) => (
          <section key={category.id} className="category-card">
            <div className="category-label-box">
              <h3 className="category-title">{category.title}</h3>
            </div>

            <div className="button-grid">
              {chunkButtons(category.items).map((row, rowIndex) => (
                <div key={`${category.id}-${rowIndex}`} className="button-row">
                  {row.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="service-button"
                      onClick={() => onSelectService(item)}
                    >
                      <span>{item.name}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div className="accessibility-bar">
        {ACCESSIBILITY_ACTIONS.map((action) => {
          const isActive = getAccessibilityActiveState(action.key, accessibility);

          return (
            <button
              key={action.key}
              type="button"
              className={`pill-button accessibility-button ${isActive ? 'active-accessibility' : ''}`}
              onClick={() => onAccessibilityAction(action.key)}
              aria-pressed={isActive}
            >
              {action.label}
            </button>
          );
        })}
      </div>
    </>
  );
}