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
  { key: 'voiceMode', label: '음성안내' },
  { key: 'highContrast', label: '고대비' },
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
      { id: 'c1', name: '가족관계증명서' },
      { id: 'c2', name: '기본증명서' },
      { id: 'c3', name: '혼인관계증명서' },
      { id: 'c4', name: '인감증명서' },
    ],
  },
  {
    id: 'personal',
    title: '민원신청',
    items: [
      { id: 'p1', name: '전입신고' },
      { id: 'p2', name: '출생신고' },
      { id: 'p3', name: '사망신고' },
    ],
  },
  {
    id: 'tax',
    title: '세금 / 납부',
    items: [
      { id: 't1', name: '지방세 납부확인서' },
      { id: 't2', name: '납세증명서' },
      { id: 't3', name: '건강보험료 납부확인서' },
    ],
  },
  {
    id: 'welfare',
    title: '복지서비스',
    items: [
      { id: 'w1', name: '복지급여 신청' },
      { id: 'w2', name: '기초생활수급자 확인' },
    ],
  },
];

export const SERVICE_CHOICES = [
  { id: 'resident-register', label: '주민등록등본 발급', documentType: '등본' },
  { id: 'resident-abstract', label: '주민등록등본(초본) 발급', documentType: '초본' },
];
