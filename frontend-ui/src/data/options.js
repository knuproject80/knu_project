export const USER_TYPES = {
  NORMAL: {
    largeFont: false,
    highContrast: false,
    simpleMode: false,
    lowScreenMode: false,
    voiceMode: false,
    fontSize: 16,
  },
  ELDERLY: {
    largeFont: true,
    highContrast: true,
    simpleMode: true,
    lowScreenMode: false,
    voiceMode: false,
    fontSize: 24,
  },
  WHEELCHAIR: {
    largeFont: false,
    highContrast: false,
    simpleMode: false,
    lowScreenMode: true,
    voiceMode: false,
    fontSize: 20,
  },
};

export const ACCESSIBILITY_ACTIONS = [
  { key: 'voiceMode', label: '음성인식' },
  { key: 'largeFont', label: '확대' },
  { key: 'lowScreenMode', label: '낮은화면' },
  { key: 'highContrast', label: '고대비' },
];

export const DEFAULT_HISTORY_OPTIONS = [
  '과거의 주소 변동사항',
  '세대 구성 정보',
  '세대 구성원 정보',
  '주민등록번호 뒷자리',
];

export const TRANSFER_REASON_OPTIONS = [
  { id: 'job', label: '직업 : 취업, 사업, 직장이전 등' },
  { id: 'family', label: '가족 : 가족과 함께 거주, 결혼, 분가 등' },
  { id: 'house', label: '주택 : 주택 구입, 계약 만료, 집세, 재개발 등' },
  { id: 'education', label: '교육 : 진학, 학업, 자녀교육 등' },
  { id: 'environment', label: '주거환경 : 교통, 문화 · 편의시설 등' },
  { id: 'nature', label: '자연환경 : 건강, 공해, 전원생활 등' },
  { id: 'etc', label: '기타' },
];

export const TRANSFER_EXTRA_SERVICES = [
  {
    id: 'lease-doc',
    label: '이·통장 등의 사후확인 생략 및 주택 임대차계약 신고(확정일자 의제)를 위한 서류 제출',
  },
  { id: 'mail-forward', label: '우편물 주소 이전 서비스 신청' },
  { id: 'school-info', label: '초등학교 배정 정보 신청' },
  { id: 'electricity-name', label: '전기사용자 명의변경 신청' },
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
      { id: 'p1', name: '전입신고', type: 'move-report' },
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
