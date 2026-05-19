export const USER_TYPES = {
  NORMAL: {
    largeFont: false,
    highContrast: false,
    simpleMode: false,
    lowScreenMode: false,
    fontSize: 16,
  },
  ELDERLY: {
    largeFont: true,
    highContrast: true,
    simpleMode: true,
    lowScreenMode: false,
    fontSize: 24,
  },
  WHEELCHAIR: {
    largeFont: false,
    highContrast: false,
    simpleMode: false,
    lowScreenMode: true,
    fontSize: 20,
  },
};

export const ACCESSIBILITY_ACTIONS = [
  { key: 'highContrast', label: '고대비' },
  { key: 'voiceGuide', label: '음성안내' },
  { key: 'largeFont', label: '확대하기' },
  { key: 'lowScreenMode', label: '낮은화면' },
];

export const DEFAULT_HISTORY_OPTIONS = [
  '과거의 주소 변동사항',
  '세대 구성 정보',
  '세대 구성원 정보',
  '주민등록번호 뒷자리',
];

export const LOCAL_SERVICE_CATEGORIES = [
  {
    id: 'certificate',
    title: '증명서발급',
    items: [
      { id: 'resident-copy', name: '주민등록등본(초본)', type: 'resident' },
      { id: 'c1', name: '버튼명 두줄가능' },
      { id: 'c2', name: '버튼명 두줄가능' },
      { id: 'c3', name: '버튼명 두줄가능' },
      { id: 'c4', name: '버튼명 두줄가능' },
      { id: 'c5', name: '버튼명 두줄가능' },
    ],
  },
  {
    id: 'personal',
    title: '민원신청',
    items: [
      { id: 'p1', name: '버튼명 두줄가능' },
      { id: 'p2', name: '버튼명 두줄가능' },
      { id: 'p3', name: '버튼명 두줄가능' },
    ],
  },
  {
    id: 'tax',
    title: '세금 / 납부',
    items: [
      { id: 't1', name: '버튼명 두줄가능' },
      { id: 't2', name: '버튼명 두줄가능' },
      { id: 't3', name: '버튼명 두줄가능' },
    ],
  },
  {
    id: 'welfare',
    title: '복지서비스',
    items: [
      { id: 'w1', name: '버튼명 두줄가능' },
      { id: 'w2', name: '기초생활수급자 확인' },
    ],
  },
];

export const SERVICE_CHOICES = [
  { id: 'resident-register', label: '주민등록등본 발급', documentType: '등본' },
  { id: 'resident-abstract', label: '주민등록등본(초본) 발급', documentType: '초본' },
];
