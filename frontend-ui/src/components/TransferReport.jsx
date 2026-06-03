import { useState } from 'react';
import { TRANSFER_EXTRA_SERVICES, TRANSFER_REASON_OPTIONS } from '../data/options';
import BottomActions from './BottomActions';
import Keypad from './Keypad';
import FlowHeader from './FlowHeader';

const TRANSFER_STEP_LABELS = [
  '기본 정보',
  '이전 주소',
  '현재 주소',
  '추가신청 서비스 선택',
  '신청 정보 확인',
];

const KEYBOARD_LAYOUTS = {
  ko: [
    ['ㅂ', 'ㅈ', 'ㄷ', 'ㄱ', 'ㅅ', 'ㅛ', 'ㅕ', 'ㅑ', 'ㅐ', 'ㅔ'],
    ['ㅁ', 'ㄴ', 'ㅇ', 'ㄹ', 'ㅎ', 'ㅗ', 'ㅓ', 'ㅏ', 'ㅣ'],
    ['쉬프트', 'ㅋ', 'ㅌ', 'ㅊ', 'ㅍ', 'ㅠ', 'ㅜ', 'ㅡ', '지우기'],
    ['한/영', '123', '기호', '공백', '완료'],
  ],
  en: [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['쉬프트', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '지우기'],
    ['한/영', '123', '기호', '공백', '완료'],
  ],
  number: [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['-', '/', '(', ')', '₩', '&', '@', '"', '.', ','],
    ['한/영', 'ABC', '기호', '공백', '지우기', '완료'],
  ],
  symbol: [
    ['!', '?', '#', '%', '^', '*', '+', '=', '~', '|'],
    ['[', ']', '{', '}', '<', '>', '_', ':', ';', '\\'],
    ['한/영', 'ABC', '123', '공백', '지우기', '완료'],
  ],
};

const MODE_KEYS = ['한/영', 'ABC', '123', '기호'];

const SHIFT_KEY_MAP = {
  ㄱ: 'ㄲ',
  ㄷ: 'ㄸ',
  ㅂ: 'ㅃ',
  ㅅ: 'ㅆ',
  ㅈ: 'ㅉ',
  ㅐ: 'ㅒ',
  ㅔ: 'ㅖ',
};

const COMPOSITE_JUNG_MAP = {
  'ㅗㅏ': 'ㅘ',
  'ㅗㅐ': 'ㅙ',
  'ㅗㅣ': 'ㅚ',
  'ㅜㅓ': 'ㅝ',
  'ㅜㅔ': 'ㅞ',
  'ㅜㅣ': 'ㅟ',
  'ㅡㅣ': 'ㅢ',
};

const COMPOSITE_JONG_MAP = {
  'ㄱㅅ': 'ㄳ',
  'ㄴㅈ': 'ㄵ',
  'ㄴㅎ': 'ㄶ',
  'ㄹㄱ': 'ㄺ',
  'ㄹㅁ': 'ㄻ',
  'ㄹㅂ': 'ㄼ',
  'ㄹㅅ': 'ㄽ',
  'ㄹㅌ': 'ㄾ',
  'ㄹㅍ': 'ㄿ',
  'ㄹㅎ': 'ㅀ',
  'ㅂㅅ': 'ㅄ',
};

const SPLIT_COMPLEX_JONG_MAP = {
  ㄳ: ['ㄱ', 'ㅅ'],
  ㄵ: ['ㄴ', 'ㅈ'],
  ㄶ: ['ㄴ', 'ㅎ'],
  ㄺ: ['ㄹ', 'ㄱ'],
  ㄻ: ['ㄹ', 'ㅁ'],
  ㄼ: ['ㄹ', 'ㅂ'],
  ㄽ: ['ㄹ', 'ㅅ'],
  ㄾ: ['ㄹ', 'ㅌ'],
  ㄿ: ['ㄹ', 'ㅍ'],
  ㅀ: ['ㄹ', 'ㅎ'],
  ㅄ: ['ㅂ', 'ㅅ'],
};

const SPLIT_JONG_TO_CHO = {
  ㄱ: 'ㄱ',
  ㄲ: 'ㄲ',
  ㄴ: 'ㄴ',
  ㄷ: 'ㄷ',
  ㄹ: 'ㄹ',
  ㅁ: 'ㅁ',
  ㅂ: 'ㅂ',
  ㅅ: 'ㅅ',
  ㅆ: 'ㅆ',
  ㅇ: 'ㅇ',
  ㅈ: 'ㅈ',
  ㅊ: 'ㅊ',
  ㅋ: 'ㅋ',
  ㅌ: 'ㅌ',
  ㅍ: 'ㅍ',
  ㅎ: 'ㅎ',
};

const CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
const JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

function isHangulSyllable(char) {
  if (!char) return false;
  const code = char.charCodeAt(0);
  return code >= 0xac00 && code <= 0xd7a3;
}

function decomposeHangul(char) {
  const code = char.charCodeAt(0) - 0xac00;
  const choIndex = Math.floor(code / (21 * 28));
  const jungIndex = Math.floor((code % (21 * 28)) / 28);
  const jongIndex = code % 28;

  return { choIndex, jungIndex, jongIndex };
}

function composeHangul(choIndex, jungIndex, jongIndex = 0) {
  return String.fromCharCode(0xac00 + (choIndex * 21 + jungIndex) * 28 + jongIndex);
}

function appendNameKey(value, key, maxLength = 12) {
  if (key === '공백') return `${value} `.slice(0, maxLength);
  if (key === '지우기') return value.slice(0, -1);

  const choIndex = CHO.indexOf(key);
  const jungIndex = JUNG.indexOf(key);
  const lastChar = value[value.length - 1];

  if (choIndex >= 0) {
    if (isHangulSyllable(lastChar)) {
      const parts = decomposeHangul(lastChar);
      const currentJong = JONG[parts.jongIndex];
      const nextSimpleJongIndex = JONG.indexOf(key);
      const compositeJong = COMPOSITE_JONG_MAP[`${currentJong}${key}`];

      // 받침이 없는 글자 뒤에 자음이 오면 받침으로 붙임: 사 + ㄹ -> 살
      if (parts.jongIndex === 0 && nextSimpleJongIndex > 0) {
        return `${value.slice(0, -1)}${composeHangul(parts.choIndex, parts.jungIndex, nextSimpleJongIndex)}`.slice(0, maxLength);
      }

      // 이미 받침이 있는 글자 뒤에 조합 가능한 자음이 오면 겹받침으로 붙임: 살 + ㅁ -> 삶
      if (parts.jongIndex > 0 && compositeJong) {
        return `${value.slice(0, -1)}${composeHangul(parts.choIndex, parts.jungIndex, JONG.indexOf(compositeJong))}`.slice(0, maxLength);
      }
    }

    return `${value}${key}`.slice(0, maxLength);
  }

  if (jungIndex >= 0) {
    const lastChoIndex = CHO.indexOf(lastChar);
    const lastStandaloneJungIndex = JUNG.indexOf(lastChar);

    // 단독 자음 + 모음 -> 한 글자로 조합: ㄱ + ㅏ -> 가
    if (lastChoIndex >= 0) {
      return `${value.slice(0, -1)}${composeHangul(lastChoIndex, jungIndex)}`.slice(0, maxLength);
    }

    // 단독 모음끼리도 복합 모음으로 조합: ㅜ + ㅔ -> ㅞ, ㅗ + ㅐ -> ㅙ
    if (lastStandaloneJungIndex >= 0) {
      const compositeStandaloneJung = COMPOSITE_JUNG_MAP[`${lastChar}${key}`];
      if (compositeStandaloneJung) {
        return `${value.slice(0, -1)}${compositeStandaloneJung}`.slice(0, maxLength);
      }
    }

    if (isHangulSyllable(lastChar)) {
      const parts = decomposeHangul(lastChar);
      const currentJung = JUNG[parts.jungIndex];
      const compositeJung = COMPOSITE_JUNG_MAP[`${currentJung}${key}`];

      // 받침 없는 음절의 중성 조합: 오 + ㅐ -> 왜, 우 + ㅔ -> 웨
      if (parts.jongIndex === 0 && compositeJung) {
        return `${value.slice(0, -1)}${composeHangul(parts.choIndex, JUNG.indexOf(compositeJung), 0)}`.slice(0, maxLength);
      }

      const jong = JONG[parts.jongIndex];
      const splitComplexJong = SPLIT_COMPLEX_JONG_MAP[jong];

      // 겹받침 뒤에 모음이 오면 뒤 자음을 다음 글자의 초성으로 이동: 삶 + ㅏ -> 살마
      if (splitComplexJong) {
        const [remainJong, nextCho] = splitComplexJong;
        const previous = composeHangul(parts.choIndex, parts.jungIndex, JONG.indexOf(remainJong));
        const next = composeHangul(CHO.indexOf(nextCho), jungIndex, 0);
        return `${value.slice(0, -1)}${previous}${next}`.slice(0, maxLength);
      }

      const splitCho = SPLIT_JONG_TO_CHO[jong];

      // 홑받침 뒤에 모음이 오면 받침을 다음 글자의 초성으로 이동: 살 + ㅏ -> 사라
      if (parts.jongIndex > 0 && splitCho) {
        const previous = composeHangul(parts.choIndex, parts.jungIndex, 0);
        const next = composeHangul(CHO.indexOf(splitCho), jungIndex, 0);
        return `${value.slice(0, -1)}${previous}${next}`.slice(0, maxLength);
      }
    }

    return `${value}${key}`.slice(0, maxLength);
  }

  return `${value}${key}`.slice(0, maxLength);
}



function getResidentDerivedInfo(residentFront, residentBack) {
  if (residentFront.length < 6 || residentBack.length < 1) {
    return {
      birthDateLabel: '주민등록번호 입력 필요',
      genderLabel: '주민등록번호 입력 필요',
    };
  }

  const yearPart = Number(residentFront.slice(0, 2));
  const month = Number(residentFront.slice(2, 4));
  const day = Number(residentFront.slice(4, 6));
  const genderCode = residentBack[0];

  const centuryMap = {
    1: 1900,
    2: 1900,
    3: 2000,
    4: 2000,
    5: 1900,
    6: 1900,
    7: 2000,
    8: 2000,
  };

  const century = centuryMap[genderCode];

  if (!century || month < 1 || month > 12 || day < 1 || day > 31) {
    return {
      birthDateLabel: '입력값 확인 필요',
      genderLabel: '입력값 확인 필요',
    };
  }

  const fullYear = century + yearPart;
  const date = new Date(fullYear, month - 1, day);
  const isValidDate =
    date.getFullYear() === fullYear &&
    date.getMonth() === month - 1 &&
    date.getDate() === day;

  if (!isValidDate) {
    return {
      birthDateLabel: '입력값 확인 필요',
      genderLabel: '입력값 확인 필요',
    };
  }

  return {
    birthDateLabel: `${fullYear}년 ${String(month).padStart(2, '0')}월 ${String(day).padStart(2, '0')}일`,
    genderLabel: Number(genderCode) % 2 === 1 ? '남' : '여',
  };
}

function RadioCircle({ checked }) {
  return <span className={`fake-radio ${checked ? 'checked' : ''}`} aria-hidden="true" />;
}

function CheckSquare({ checked }) {
  return <span className={`fake-checkbox ${checked ? 'checked' : ''}`} aria-hidden="true" />;
}

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

function TransferShell({ title, currentStep, children, onHome, onPrev, onNext, nextLabel = '다음', disableNext }) {
  return (
    <>
      <section className="content-panel transfer-panel">
        <FlowHeader title={title} currentStep={currentStep} labels={TRANSFER_STEP_LABELS} />
        <div className="content-body-frame body-left-frame transfer-body">{children}</div>
      </section>

      <BottomActions
        onHome={onHome}
        onPrev={onPrev}
        onNext={onNext}
        nextLabel={nextLabel}
        disableNext={disableNext}
      />
    </>
  );
}

function TextKeyboard({ onPress }) {
  const [keyboardMode, setKeyboardMode] = useState('ko');
  const [shiftActive, setShiftActive] = useState(false);

  const rows = KEYBOARD_LAYOUTS[keyboardMode];

  const changeMode = (nextMode) => {
    setKeyboardMode(nextMode);
    setShiftActive(false);
  };

  const handleKeyPress = (key) => {
    if (key === '쉬프트') {
      setShiftActive((prev) => !prev);
      return;
    }

    if (key === '한/영') {
      changeMode(keyboardMode === 'ko' ? 'en' : 'ko');
      return;
    }

    if (key === 'ABC') {
      changeMode('en');
      return;
    }

    if (key === '123') {
      changeMode('number');
      return;
    }

    if (key === '기호') {
      changeMode('symbol');
      return;
    }

    const pressedKey = keyboardMode === 'en' && shiftActive
      ? key.toUpperCase()
      : shiftActive
        ? SHIFT_KEY_MAP[key] || key
        : key;

    onPress(pressedKey);

    if (shiftActive && !['공백', '지우기', '완료'].includes(key)) {
      setShiftActive(false);
    }
  };

  const getLabel = (key) => {
    if (keyboardMode === 'en' && shiftActive && /^[a-z]$/.test(key)) {
      return key.toUpperCase();
    }

    if (keyboardMode === 'ko' && shiftActive) {
      return SHIFT_KEY_MAP[key] || key;
    }

    return key;
  };

  const getKeyClass = (key) => {
    if (key === '공백') return 'control space-key';
    if (key === '쉬프트') return 'control action-key shift-key';
    if (key === '지우기' || key === '완료') return 'control action-key';
    if (MODE_KEYS.includes(key)) return 'control mode-key';
    return 'letter-key';
  };

  const isModeActive = (key) => {
    if (key === '한/영') return keyboardMode === 'ko' || keyboardMode === 'en';
    if (key === 'ABC') return keyboardMode === 'en';
    if (key === '123') return keyboardMode === 'number';
    if (key === '기호') return keyboardMode === 'symbol';
    return false;
  };

  return (
    <div className={`text-keyboard text-keyboard-${keyboardMode}`} aria-label="텍스트 입력 키보드">
      {rows.map((row, rowIndex) => (
        <div key={`name-row-${rowIndex}`} className="text-keyboard-row">
          {row.map((key) => {
            const label = getLabel(key);
            const isShiftActive = key === '쉬프트' && shiftActive;
            const isActiveModeKey = isModeActive(key);

            return (
              <button
                key={`${keyboardMode}-${rowIndex}-${key}`}
                type="button"
                className={`text-keyboard-button ${getKeyClass(key)} ${isShiftActive ? 'shift-active' : ''} ${isActiveModeKey ? 'mode-active' : ''} ${key === '지우기' ? 'delete-key-button' : ''}`}
                onClick={() => handleKeyPress(key)}
                aria-pressed={key === '쉬프트' ? shiftActive : MODE_KEYS.includes(key) ? isActiveModeKey : undefined}
                aria-label={key === '지우기' ? '지우기' : undefined}
              >
                {key === '지우기' ? <DeleteKeyIcon /> : label}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function KeyboardPreview({ activeInput, data }) {
  if (!activeInput) return null;

  if (activeInput === 'phone2' || activeInput === 'phone3') {
    return (
      <div className="keyboard-preview" aria-label="휴대전화번호 입력 상태">
        <p className="keyboard-preview-label">휴대전화번호 <span>(필수)</span></p>
        <div className="keyboard-preview-phone-row">
          <div className="keyboard-preview-input">010</div>
          <span className="transfer-hyphen">-</span>
          <div className={`keyboard-preview-input ${activeInput === 'phone2' ? 'active' : ''}`}>{data.phone2}</div>
          <span className="transfer-hyphen">-</span>
          <div className={`keyboard-preview-input ${activeInput === 'phone3' ? 'active' : ''}`}>{data.phone3}</div>
        </div>
      </div>
    );
  }

  if (activeInput === 'resident') {
    return (
      <div className="keyboard-preview" aria-label="주민등록번호 입력 상태">
        <p className="keyboard-preview-label">주민등록번호 입력 <span>(필수)</span></p>
        <div className="keyboard-preview-resident-row">
          <div className="keyboard-preview-input">{data.residentFront}</div>
          <span className="transfer-hyphen">-</span>
          <div className="keyboard-preview-input">{'●'.repeat(data.residentBack.length)}</div>
        </div>
      </div>
    );
  }


  const textPreviewMap = {
    currentBaseAddress: { label: '기본 주소', required: true, value: data.currentBaseAddress },
    buildingMainNo: { label: '본번', required: true, value: data.buildingMainNo },
    buildingSubNo: { label: '부번', required: false, value: data.buildingSubNo },
    detailAddress: { label: '그 외 주소', required: false, value: data.detailAddress },
  };

  const preview = textPreviewMap[activeInput];
  if (preview) {
    return (
      <div className="keyboard-preview" aria-label={`${preview.label} 입력 상태`}>
        <p className="keyboard-preview-label">
          {preview.label} {preview.required ? <span>(필수)</span> : null}
        </p>
        <div className="keyboard-preview-text-row">
          <div className="keyboard-preview-input active text-preview-input">
            {preview.value}
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function KeyboardPanel({ type, activeInput, data, onNamePress, onNumberPress }) {
  if (!type) return null;

  return (
    <div className="transfer-keyboard-panel">
      <KeyboardPreview activeInput={activeInput} data={data} />
      {type === 'name' ? <TextKeyboard onPress={onNamePress} /> : <Keypad onPress={onNumberPress} />}
    </div>
  );
}

export function TransferIdentityInfo({ data, onChange, onResidentKeypad, onHome, onPrev, onNext }) {
  const [activeInput, setActiveInput] = useState(null);
  const disableNext =
    !data.name.trim() ||
    data.residentFront.length < 6 ||
    data.residentBack.length < 7 ||
    data.phone2.length < 4 ||
    data.phone3.length < 4;

  const handleNameKeyboard = (key) => {
    if (key === '완료') {
      setActiveInput(null);
      return;
    }

    onChange('name', appendNameKey(data.name, key));
  };

  const handlePhoneKeypad = (key) => {
    if (activeInput !== 'phone2' && activeInput !== 'phone3') return;

    if (key === '완료') {
      setActiveInput(null);
      return;
    }

    if (key === 'X') {
      if (data[activeInput].length > 0) {
        onChange(activeInput, data[activeInput].slice(0, -1));
        return;
      }

      if (activeInput === 'phone3') {
        setActiveInput('phone2');
      }
      return;
    }

    if (!/^\d$/.test(key)) return;

    const currentValue = data[activeInput];
    if (currentValue.length >= 4) return;

    const nextValue = `${currentValue}${key}`.slice(0, 4);
    onChange(activeInput, nextValue);

    if (activeInput === 'phone2' && nextValue.length >= 4) {
      setActiveInput('phone3');
    }
  };

  const handleNumberKeyboard = (key) => {
    if (key === '완료') {
      setActiveInput(null);
      return;
    }

    if (activeInput === 'resident') {
      onResidentKeypad(key);
      return;
    }

    handlePhoneKeypad(key);
  };

  return (
    <TransferShell
      title="본인확인 및 기본정보를 입력해주세요."
      currentStep={1}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
      disableNext={disableNext}
    >
      <section className="transfer-card identity-input-card">
        <h3 className="transfer-card-title">본인확인 및 기본정보 입력</h3>

        <div className="transfer-field-block">
          <label className="transfer-field-label" htmlFor="transfer-name-input">신청인 성명</label>
          <input
            id="transfer-name-input"
            className="transfer-input name-input"
            value={data.name}
            onFocus={() => setActiveInput('name')}
            onClick={() => setActiveInput('name')}
            onChange={() => {}}
            placeholder=""
            readOnly
            aria-label="신청인 성명"
          />
        </div>

        <div className="transfer-field-block">
          <label className="transfer-field-label">주민등록번호 입력 <span>(필수)</span></label>
          <div className="transfer-resident-row">
            <button
              type="button"
              className="masked-input transfer-resident-input input-like-button"
              onClick={() => setActiveInput('resident')}
              aria-label="주민등록번호 앞자리 입력"
            >
              {data.residentFront}
            </button>
            <span className="hyphen">-</span>
            <button
              type="button"
              className="masked-input transfer-resident-input input-like-button"
              onClick={() => setActiveInput('resident')}
              aria-label="주민등록번호 뒷자리 입력"
            >
              {'●'.repeat(data.residentBack.length)}
            </button>
          </div>
        </div>

        <div className="transfer-field-block phone-block">
          <label className="transfer-field-label">휴대전화번호 <span>(필수)</span></label>
          <div className="transfer-phone-row">
            <input
              className="transfer-input phone-input fixed-phone-input"
              value="010"
              readOnly
              aria-label="휴대전화번호 앞자리"
            />
            <span className="transfer-hyphen">-</span>
            <input
              className="transfer-input phone-input"
              value={data.phone2}
              onFocus={() => setActiveInput('phone2')}
              onClick={() => setActiveInput('phone2')}
              onChange={() => {}}
              inputMode="none"
              readOnly
              aria-label="휴대전화번호 가운데 자리"
            />
            <span className="transfer-hyphen">-</span>
            <input
              className="transfer-input phone-input"
              value={data.phone3}
              onFocus={() => setActiveInput('phone3')}
              onClick={() => setActiveInput('phone3')}
              onChange={() => {}}
              inputMode="none"
              readOnly
              aria-label="휴대전화번호 뒷자리"
            />
          </div>
        </div>
      </section>

      <KeyboardPanel
        type={activeInput === 'name' ? 'name' : activeInput ? 'number' : null}
        activeInput={activeInput}
        data={data}
        onNamePress={handleNameKeyboard}
        onNumberPress={handleNumberKeyboard}
      />
    </TransferShell>
  );
}

export function TransferReason({ data, onSelectReason, onHome, onPrev, onNext }) {
  const disableNext = !data.reason;

  return (
    <TransferShell
      title="전입사유를 입력해주세요."
      currentStep={1}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
      disableNext={disableNext}
    >
      <section className="transfer-card reason-only-card">
        <h3 className="transfer-card-title">전입사유 선택</h3>
        <p className="transfer-sub-label">구분 <span>(필수)</span></p>

        <div className="transfer-reason-grid">
          {TRANSFER_REASON_OPTIONS.map((reason) => (
            <button
              key={reason.id}
              type="button"
              className={`transfer-option-button ${data.reason === reason.id ? 'selected' : ''}`}
              onClick={() => onSelectReason(reason.id)}
            >
              <RadioCircle checked={data.reason === reason.id} />
              <span>{reason.label}</span>
            </button>
          ))}
        </div>
      </section>
    </TransferShell>
  );
}

export function TransferPreviousInfo({ data, onChange, onToggleMember, onHome, onPrev, onNext }) {
  const disableNext = data.movingMembers.length === 0;
  const residentInfo = getResidentDerivedInfo(data.residentFront, data.residentBack);

  return (
    <TransferShell
      title="이사 전 거주지 정보를 입력해주세요."
      currentStep={2}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
      disableNext={disableNext}
    >
      <section className="transfer-card previous-info-card">
        <h3 className="transfer-card-title">이전 주소 검색 및 확인</h3>
        <p className="transfer-sub-label">주소 확인</p>

        <div className="transfer-address-search-row">
          <select
            className="transfer-input transfer-select"
            value={data.prevSido}
            onChange={(event) => onChange('prevSido', event.target.value)}
            aria-label="시도 선택"
          >
            <option>대구광역시</option>
            <option>서울특별시</option>
            <option>부산광역시</option>
          </select>

          <select
            className="transfer-input transfer-select"
            value={data.prevSigungu}
            onChange={(event) => onChange('prevSigungu', event.target.value)}
            aria-label="시군구 선택"
          >
            <option>북구</option>
            <option>중구</option>
            <option>수성구</option>
            <option>달서구</option>
          </select>

          <button type="button" className="transfer-search-button">
            주소조회
          </button>
        </div>

        <div className="transfer-info-table address-table">
          <div className="transfer-table-label">기본 주소</div>
          <div className="transfer-table-value">{data.prevAddress}</div>
          <div className="transfer-table-label">관할 읍·면·동 행정복지센터</div>
          <div className="transfer-table-value">{data.prevAdminCenter}</div>
        </div>
      </section>

      <section className="transfer-card moving-member-card">
        <h3 className="transfer-card-title">이사 가는 사람 선택 <span>(필수)</span></h3>

        <div className="transfer-person-table">
          <div className="transfer-person-head select-col">
            <CheckSquare checked={data.movingMembers.includes('self')} />
          </div>
          <div className="transfer-person-head">세대주와의 관계</div>
          <div className="transfer-person-head">성명</div>
          <div className="transfer-person-head">생년월일</div>
          <div className="transfer-person-head">성별</div>

          <button
            type="button"
            className="transfer-person-cell select-col selectable-cell"
            onClick={() => onToggleMember('self')}
            aria-label="본인 선택"
          >
            <CheckSquare checked={data.movingMembers.includes('self')} />
          </button>
          <div className="transfer-person-cell">본인 <span className="text-blue">(신청인)</span></div>
          <div className="transfer-person-cell">{data.name || '신청인'}</div>
          <div className="transfer-person-cell">{residentInfo.birthDateLabel}</div>
          <div className="transfer-person-cell">{residentInfo.genderLabel}</div>
        </div>
      </section>
    </TransferShell>
  );
}

export function TransferCurrentAddressInfo({ data, onChange, onHome, onPrev, onNext }) {
  const [activeInput, setActiveInput] = useState(null);
  const disableNext = !data.currentBaseAddress || !data.buildingMainNo;

  const isTextInput = activeInput === 'currentBaseAddress' || activeInput === 'detailAddress';
  const isNumberInput = activeInput === 'buildingMainNo' || activeInput === 'buildingSubNo';

  const handleAddressTextKeyboard = (key) => {
    if (!isTextInput) return;

    if (key === '완료') {
      setActiveInput(null);
      return;
    }

    const maxLength = activeInput === 'currentBaseAddress' ? 40 : 60;
    onChange(activeInput, appendNameKey(data[activeInput] || '', key, maxLength));
  };

  const handleAddressNumberKeypad = (key) => {
    if (!isNumberInput) return;

    if (key === '완료') {
      setActiveInput(null);
      return;
    }

    if (key === 'X') {
      onChange(activeInput, (data[activeInput] || '').slice(0, -1));
      return;
    }

    if (!/^\d$/.test(key)) return;

    onChange(activeInput, `${data[activeInput] || ''}${key}`.slice(0, 5));
  };

  return (
    <TransferShell
      title="이사 후(현재) 거주지 정보를 입력해주세요."
      currentStep={3}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
      disableNext={disableNext}
    >
      <section className="transfer-card current-address-card">
        <h3 className="transfer-card-title">현주소 정보 입력</h3>
        <p className="transfer-sub-label">주소 확인 <span>(필수)</span></p>

        <div className="transfer-field-block">
          <label className="transfer-field-label">기본 주소</label>
          <div className="transfer-address-input-row">
            <input
              className="transfer-input base-address-input"
              value={data.currentBaseAddress}
              onFocus={() => setActiveInput('currentBaseAddress')}
              onClick={() => setActiveInput('currentBaseAddress')}
              onChange={() => {}}
              inputMode="none"
              readOnly
              placeholder="전입할 기본주소를 입력하세요."
              aria-label="전입할 기본주소"
            />
            <button type="button" className="transfer-search-button wide">검색</button>
          </div>
        </div>

        <div className="transfer-number-grid">
          <div className="transfer-field-block">
            <label className="transfer-field-label">건축물 구분</label>
            <select
              className="transfer-input transfer-select full"
              value={data.buildingType}
              onChange={(event) => onChange('buildingType', event.target.value)}
            >
              <option value="ground">지상</option>
              <option value="underground">지하</option>
            </select>
          </div>

          <div className="transfer-field-block">
            <label className="transfer-field-label">본번</label>
            <input
              className="transfer-input"
              value={data.buildingMainNo}
              onFocus={() => setActiveInput('buildingMainNo')}
              onClick={() => setActiveInput('buildingMainNo')}
              onChange={() => {}}
              inputMode="none"
              readOnly
              aria-label="건물번호 본번"
            />
          </div>

          <div className="transfer-field-block">
            <label className="transfer-field-label">부번</label>
            <input
              className="transfer-input"
              value={data.buildingSubNo}
              onFocus={() => setActiveInput('buildingSubNo')}
              onClick={() => setActiveInput('buildingSubNo')}
              onChange={() => {}}
              inputMode="none"
              readOnly
              aria-label="건물번호 부번"
            />
          </div>
        </div>

        <div className="transfer-field-block detail-address-block">
          <label className="transfer-field-label">그 외 주소</label>
          <input
            className="transfer-input detail-address-input"
            value={data.detailAddress}
            onFocus={() => setActiveInput('detailAddress')}
            onClick={() => setActiveInput('detailAddress')}
            onChange={() => {}}
            inputMode="none"
            readOnly
            placeholder="상세주소를 입력하세요. 입력 예시 : 101동 501호(인사동, 무궁화 아파트)"
            aria-label="그 외 주소"
          />
        </div>

      </section>

      <KeyboardPanel
        type={isTextInput ? 'name' : isNumberInput ? 'number' : null}
        activeInput={activeInput}
        data={data}
        onNamePress={handleAddressTextKeyboard}
        onNumberPress={handleAddressNumberKeypad}
      />
    </TransferShell>
  );
}

export function TransferHousehold({ data, onChange, onHome, onPrev, onNext }) {
  const disableNext = !data.householdType;

  return (
    <TransferShell
      title="이사 후(현재) 거주지 정보를 입력해주세요."
      currentStep={3}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
      disableNext={disableNext}
    >
      <section className="transfer-card household-card">
        <h3 className="transfer-card-title">세대구성 방법 선택</h3>
        <p className="transfer-sub-label">세대 구성 방법 <span>(필수)</span></p>

        <div className="transfer-radio-list compact">
          <button
            type="button"
            className={`transfer-option-button ${data.householdType === 'new' ? 'selected' : ''}`}
            onClick={() => onChange('householdType', 'new')}
          >
            <RadioCircle checked={data.householdType === 'new'} />
            <span>이사온 사람끼리 세대 구성 (빈집으로 이사)</span>
          </button>
          <button
            type="button"
            className={`transfer-option-button ${data.householdType === 'join' ? 'selected' : ''}`}
            onClick={() => onChange('householdType', 'join')}
          >
            <RadioCircle checked={data.householdType === 'join'} />
            <span>이사온 곳에 기존에 살고 있는 세대주가 있는 경우</span>
          </button>
        </div>
      </section>
    </TransferShell>
  );
}

export function TransferExtraService({ data, onToggleExtraService, onHome, onPrev, onNext }) {
  return (
    <TransferShell
      title="전입신고와 함께 신청할 수 있는 서비스입니다."
      currentStep={4}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onNext}
    >
      <section className="transfer-card extra-service-card">
        <h3 className="transfer-card-title">추가신청 서비스 선택</h3>

        <div className="transfer-extra-list">
          {TRANSFER_EXTRA_SERVICES.map((service) => (
            <button
              key={service.id}
              type="button"
              className={`transfer-extra-row ${data.extraServices.includes(service.id) ? 'selected' : ''}`}
              onClick={() => onToggleExtraService(service.id)}
            >
              <CheckSquare checked={data.extraServices.includes(service.id)} />
              <span>{service.label}</span>
              <span className="transfer-row-arrow">⌄</span>
            </button>
          ))}
        </div>
      </section>
    </TransferShell>
  );
}

function findTransferReasonLabel(reasonId) {
  return TRANSFER_REASON_OPTIONS.find((item) => item.id === reasonId)?.label || '미선택';
}

function findHouseholdLabel(householdType) {
  if (householdType === 'new') return '이사온 사람끼리 세대 구성 (빈집으로 이사)';
  if (householdType === 'join') return '이사온 곳에 기존에 살고 있는 세대주가 있는 경우';
  return '미선택';
}

function findExtraServiceLabels(serviceIds) {
  if (!serviceIds.length) return ['선택한 부가 서비스 없음'];
  return serviceIds.map((id) => TRANSFER_EXTRA_SERVICES.find((service) => service.id === id)?.label || id);
}

export function TransferConfirm({ data, onHome, onPrev, onSubmit }) {
  const residentNumber = `${data.residentFront || ''}-${data.residentBack ? '●'.repeat(data.residentBack.length) : ''}`;
  const buildingNumber = data.buildingSubNo ? `${data.buildingMainNo}-${data.buildingSubNo}` : data.buildingMainNo;
  const currentAddress = [data.currentBaseAddress, buildingNumber ? `건물번호 ${buildingNumber}` : '', data.detailAddress]
    .filter(Boolean)
    .join('\n');

  return (
    <TransferShell
      title="신청 정보를 확인해주세요."
      currentStep={5}
      onHome={onHome}
      onPrev={onPrev}
      onNext={onSubmit}
      nextLabel="제출"
    >
      <section className="transfer-card transfer-confirm-card">
        <h3 className="transfer-card-title">전입신고 신청 정보 확인</h3>

        <div className="transfer-summary-grid">
          <div className="transfer-summary-block">
            <h4>신청인 정보</h4>
            <p><strong>성명</strong><span>{data.name || '미입력'}</span></p>
            <p><strong>주민등록번호</strong><span>{residentNumber}</span></p>
            <p><strong>휴대전화번호</strong><span>{data.phone1}-{data.phone2}-{data.phone3}</span></p>
            <p><strong>전입사유</strong><span>{findTransferReasonLabel(data.reason)}</span></p>
          </div>

          <div className="transfer-summary-block">
            <h4>이전 주소</h4>
            <p><strong>기본주소</strong><span>{data.prevAddress}</span></p>
            <p><strong>관할센터</strong><span>{data.prevAdminCenter}</span></p>
            <p><strong>이사 가는 사람</strong><span>{data.movingMembers.includes('self') ? `${data.name || '김성애'} (본인)` : '미선택'}</span></p>
          </div>

          <div className="transfer-summary-block">
            <h4>현재 주소</h4>
            <p><strong>기본주소</strong><span>{currentAddress || '미입력'}</span></p>
            <p><strong>건축물 구분</strong><span>{data.buildingType === 'underground' ? '지하' : '지상'}</span></p>
            <p><strong>세대구성</strong><span>{findHouseholdLabel(data.householdType)}</span></p>
          </div>

          <div className="transfer-summary-block">
            <h4>추가신청 서비스</h4>
            <ul>
              {findExtraServiceLabels(data.extraServices).map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </TransferShell>
  );
}