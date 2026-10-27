export const navItems = [
  { label: 'Преподаватели', href: '/teachers' },
  { label: 'Предметы', href: '/catalog' },
  { label: 'ЕГЭ/ОГЭ', href: '/exams' },
  { label: 'Программирование', href: '/programming' },
  { label: 'Языки', href: '/languages' },
  { label: 'Отзывы', href: '/reviews' },
]

export const stats = [
  { value: '30+', label: 'направлений', icon: 'books' },
  { value: '50 000+', label: 'учеников', icon: 'users' },
  { value: '4.9', label: 'средняя оценка', icon: 'rating' },
  { value: '85%', label: 'поступают на бюджет', icon: 'graduation' },
]

export const directions = [
  {
    title: 'Школьные предметы',
    description: 'Математика, русский язык, физика, химия, литература и другие предметы.',
    icon: 'books',
    href: '/catalog',
  },
  {
    title: 'ЕГЭ и ОГЭ',
    description: 'План подготовки, пробники, разбор ошибок и контроль динамики баллов.',
    icon: 'exam',
    href: '/exams',
  },
  {
    title: 'Иностранные языки',
    description: 'Английский, немецкий, французский, испанский и международные экзамены.',
    icon: 'language',
    href: '/languages',
  },
  {
    title: 'Международные экзамены',
    description: 'IELTS, TOEFL, HSK, JLPT, DELF и другие международные сертификаты.',
    icon: 'badge',
    href: '/languages',
  },
  {
    title: 'Разработка и IT',
    description: 'Языки программирования, разработка игр, алгоритмы, профессии в IT.',
    icon: 'code',
    href: '/programming',
  },
]

export const courseCards = [
  {
    title: 'Математика ЕГЭ',
    tag: 'ЕГЭ',
    subtitle: 'профильный уровень',
    price: 'от 2 490 ₽ / мес.',
    icon: 'sum',
    tint: 'peach',
  },
  {
    title: 'Информатика ОГЭ',
    tag: 'ОГЭ',
    subtitle: 'кодинг + теория',
    price: 'от 2 190 ₽ / мес.',
    icon: 'code',
    tint: 'sky',
  },
  {
    title: 'Русский язык ЕГЭ',
    tag: 'ЕГЭ',
    subtitle: 'сочинение + тест',
    price: 'от 2 390 ₽ / мес.',
    icon: 'language',
    tint: 'violet',
  },
  {
    title: 'Английский язык IELTS',
    tag: 'IELTS',
    subtitle: 'A2-C1 · Speaking',
    price: 'от 2 990 ₽ / мес.',
    icon: 'ielts',
    tint: 'mint',
  },
  {
    title: 'Разработка игр на Unity',
    tag: 'проект',
    subtitle: 'для начинающих',
    price: 'от 3 490 ₽ / мес.',
    icon: 'game',
    tint: 'rose',
  },
  {
    title: 'Физика 5-11 классы',
    tag: 'школа',
    subtitle: 'формулы и задачи',
    price: 'от 1 990 ₽ / мес.',
    icon: 'physics',
    tint: 'sky',
  },
]

export const workflowSteps = [
  {
    title: 'Начните бесплатно',
    text: 'Определим уровень знаний и цель обучения.',
    icon: 'search',
  },
  {
    title: 'Получите план',
    text: 'Соберём персональную программу обучения.',
    icon: 'clipboard',
  },
  {
    title: 'Занимайтесь',
    text: 'Посещайте уроки, выполняйте задания и получайте проверку.',
    icon: 'play',
  },
  {
    title: 'Отслеживайте прогресс',
    text: 'Смотрите результаты и рекомендации в личном кабинете.',
    icon: 'chart',
  },
  {
    title: 'Достигайте целей',
    text: 'Уверенно сдавайте экзамены и получайте новые навыки.',
    icon: 'target',
  },
]

export const teachers = [
  {
    name: 'Алексей В.',
    role: 'Преподаватель математики',
    description: 'Готовлю к ЕГЭ больше 10 лет. Мои ученики стабильно набирают 80+ баллов.',
    rating: '4.9',
    initials: 'АВ',
  },
  {
    name: 'Мария С.',
    role: 'Преподаватель английского',
    description: 'Сдала IELTS на 8.5 и помогаю ученикам уверенно достигать своих целей.',
    rating: '5.0',
    initials: 'МС',
  },
  {
    name: 'Игорь К.',
    role: 'Преподаватель IT',
    description: 'Учу программировать на практике и готовлю к реальным задачам индустрии.',
    rating: '4.9',
    initials: 'ИК',
  },
  {
    name: 'Ирина Волкова',
    role: 'Русский язык',
    description: 'Разбираем сочинения, тестовую часть и ловушки экзамена без паники.',
    rating: '5.0',
    initials: 'ИВ',
  },
  {
    name: 'Дмитрий Ковалёв',
    role: 'Английский язык',
    description: 'Делаем упор на разговорную практику, грамматику и уверенность на экзамене.',
    rating: '4.8',
    initials: 'ДК',
  },
  {
    name: 'Екатерина Лебедева',
    role: 'Литература',
    description: 'Помогаю видеть структуру произведений и писать сильные аргументы.',
    rating: '4.9',
    initials: 'ЕЛ',
  },
]

export const pricingPlans = [
  {
    name: 'Школьная программа',
    description: 'Для уверенного понимания предмета',
    price: 'от 500 ₽ / занятие',
    features: ['Репетитор под ваш уровень', 'Персональный темп', 'Онлайн-формат'],
  },
  {
    name: 'ОГЭ / ЕГЭ',
    description: 'Для системной подготовки к экзаменам',
    price: 'от 1 000 ₽ / занятие',
    popular: true,
    features: ['Опыт подготовки к экзаменам', 'Работа над типовыми заданиями', 'Индивидуальная стратегия'],
  },
  {
    name: 'Углублённая подготовка',
    description: 'Для высоких баллов и сложных целей',
    price: 'от 1 000 ₽ / занятие',
    features: ['Сильные преподаватели', 'Углублённый разбор тем', 'Интенсивный формат'],
  },
]

export const examSubjects = [
  { title: 'Математика', subtitle: 'профильный уровень', price: 'от 2 390 ₽ / мес.', icon: 'sum' },
  { title: 'Русский язык', subtitle: 'сочинение и тест', price: 'от 2 190 ₽ / мес.', icon: 'language' },
  { title: 'Обществознание', subtitle: 'теория и практика', price: 'от 2 490 ₽ / мес.', icon: 'history' },
  { title: 'Физика', subtitle: 'формулы и задачи', price: 'от 2 490 ₽ / мес.', icon: 'physics' },
  { title: 'Информатика', subtitle: 'кодинг и алгоритмы', price: 'от 2 590 ₽ / мес.', icon: 'code' },
  { title: 'Биология', subtitle: 'системная подготовка', price: 'от 2 390 ₽ / мес.', icon: 'biology' },
]

export const programmingTracks = [
  { title: 'Python', text: 'Разработка на Python с нуля до профи', price: 'от 2 590 ₽ / мес.', icon: 'python' },
  { title: 'Веб-разработка', text: 'Сайты и веб-приложения на HTML, CSS, JS', price: 'от 2 690 ₽ / мес.', icon: 'web' },
  { title: 'Спортивное программирование', text: 'Алгоритмы, структуры данных, соревнования', price: 'от 2 990 ₽ / мес.', icon: 'target' },
  { title: 'Разработка игр', text: '2D/3D игры на Unity и логика геймплея', price: 'от 3 390 ₽ / мес.', icon: 'game' },
  { title: 'Алгоритмы и структуры данных', text: 'Подготовка к олимпиадам и техническим интервью', price: 'от 2 490 ₽ / мес.', icon: 'network' },
  { title: 'Промышленное программирование', text: 'Backend, базы данных, DevOps и тестирование', price: 'от 3 990 ₽ / мес.', icon: 'robot' },
]

export const languageExams = [
  { title: 'IELTS', text: 'Международный экзамен по английскому языку', price: 'от 2 990 ₽ / мес.', icon: 'ielts' },
  { title: 'TOEFL', text: 'Тест на знание английского языка', price: 'от 2 990 ₽ / мес.', icon: 'toefl' },
  { title: 'Cambridge', text: 'KET, PET, FCE, CAE, CPE', price: 'от 2 990 ₽ / мес.', icon: 'certificate' },
  { title: 'HSK', text: 'Экзамен по китайскому языку', price: 'от 2 490 ₽ / мес.', icon: 'hsk' },
  { title: 'JLPT', text: 'Экзамен по японскому языку', price: 'от 2 490 ₽ / мес.', icon: 'jlpt' },
  { title: 'DELE', text: 'Экзамен по испанскому языку', price: 'от 2 490 ₽ / мес.', icon: 'dele' },
]

export const reviews = [
  {
    subject: 'ЕГЭ',
    name: 'Алёна С.',
    title: 'Русский язык · 94 балла',
    text: 'Занималась 6 месяцев. Очень помогли разборы сочинений и практика с наставником.',
    result: '94',
  },
  {
    subject: 'ОГЭ',
    name: 'Игорь К.',
    title: 'Математика · 5 отлично',
    text: 'Благодаря заданиям в кабинете всё стало понятно, и я сдал на максимум.',
    result: '5',
  },
  {
    subject: 'IELTS',
    name: 'Мария Л.',
    title: 'Английский язык · IELTS 7.5',
    text: 'Системная подготовка и разговорная практика дали отличный результат.',
    result: '7.5',
  },
  {
    subject: 'IT',
    name: 'Дмитрий П.',
    title: 'Python · проект в портфолио',
    text: 'Занятия помогли прокачать навыки и получить работу мечты.',
    result: '</>',
  },
]

export const faqItems = [
  {
    question: 'Как начать обучение?',
    answer: 'Начните бесплатно, и мы подберём подходящий предмет, преподавателя и формат занятий.',
  },
  {
    question: 'Можно ли вернуть оплату?',
    answer: 'Да, условия возврата фиксируются в договоре перед началом обучения.',
  },
  {
    question: 'Как проверяются домашние задания?',
    answer: 'Задания проверяют преподаватели и наставники с подробной обратной связью.',
  },
]

