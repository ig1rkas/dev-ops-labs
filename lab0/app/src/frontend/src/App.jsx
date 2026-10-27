import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import './styles.css'
import { Icon } from './components/Icon.jsx'
import { Logo } from './components/Logo.jsx'
import { RedPanda } from './components/RedPanda.jsx'
import {
  courseCards as fallbackCourseCards,
  directions,
  examSubjects as fallbackExamSubjects,
  languageExams as fallbackLanguageExams,
  navItems,
  pricingPlans,
  programmingTracks as fallbackProgrammingTracks,
  reviews,
  stats,
  teachers as fallbackTeachers,
  workflowSteps,
} from './data/siteData.js'
import { SESSION_STORAGE_KEY, assignStudentToTeacher, changePassword, createAdminStudent, createAdminSubject, createAdminTeacher, createCourseRequest, createTeacherApplication, deleteAdminSubject, deleteAdminUser, deleteChatMessage, deleteCourseRequest, deleteTeacherApplication, fetchAdminDashboard, fetchAdminUser, fetchAdminUsers, fetchChat, fetchChatDocument, fetchChatPhoto, fetchChats, fetchCourseRequests, fetchStudentDashboard, fetchTeacherApplications, fetchTeacherDashboard, fetchTeacherStudents, fetchSubjects, fetchTeachers, fetchTelegramStatus, getMe, login, register, removeStudentFromTeacher, reorderAdminTeacher, scheduleCourseRequest, sendChatDocument, sendChatMessage, sendChatPhoto, updateAdminTeacher, updateStudentSettings, updateTeacherStudentDisplayName } from './services/api.js'

const getPath = () => window.location.pathname || '/'
const isMobileViewport = () => typeof window !== 'undefined' && window.matchMedia?.('(max-width: 760px)').matches
const getDashboardInitialTab = (role) => (isMobileViewport() ? (role === 'student' ? 'schedule' : 'messages') : 'overview')

function useResponsiveDashboardTabs(setActiveTab, role) {
  useEffect(() => {
    const media = window.matchMedia?.('(max-width: 760px)')
    if (!media) return undefined
    const mobileTabs = role === 'student'
      ? ['schedule', 'settings']
      : role === 'admin'
        ? ['messages', 'teachers']
        : ['messages', 'schedule', 'settings']
    const fallbackTab = role === 'student' ? 'schedule' : 'messages'
    const syncTab = () => {
      if (!media.matches) return
      setActiveTab((current) => mobileTabs.includes(current) ? current : fallbackTab)
    }
    syncTab()
    media.addEventListener?.('change', syncTab)
    return () => media.removeEventListener?.('change', syncTab)
  }, [role, setActiveTab])
}

const weekDayOptions = [
  { value: 0, label: 'Понедельник' },
  { value: 1, label: 'Вторник' },
  { value: 2, label: 'Среда' },
  { value: 3, label: 'Четверг' },
  { value: 4, label: 'Пятница' },
  { value: 5, label: 'Суббота' },
  { value: 6, label: 'Воскресенье' },
]

const createScheduleSlot = () => ({ weekday: '1', time: '13:00' })
const getScheduleSlots = (form = {}) => (form.slots?.length ? form.slots : [createScheduleSlot()])

const categoryLabels = {
  school: 'Школьные предметы',
  exams: 'ЕГЭ и ОГЭ',
  international: 'Международные экзамены',
  languages: 'Иностранные языки',
  programming: 'Программирование',
}

const catalogFilters = [
  { label: 'Все предметы', value: 'all' },
  { label: 'Школьные предметы', value: 'school' },
  { label: 'ЕГЭ', value: 'ege' },
  { label: 'ОГЭ', value: 'oge' },
  { label: 'Языки', value: 'international' },
  { label: 'Иностранные языки', value: 'languages' },
  { label: 'Программирование', value: 'programming' },
]

const teacherFilters = [
  { label: 'Все категории', value: 'all' },
  { label: 'ЕГЭ и ОГЭ', value: 'exams' },
  { label: 'Языки', value: 'international' },
  { label: 'Иностранные языки', value: 'languages' },
  { label: 'Программирование', value: 'programming' },
  { label: 'Школа', value: 'school' },
]

const TEACHER_PRICE_MAX = 20_000

const subjectIconOptions = [
  ['book', 'Книга'], ['sum', 'Математика'], ['language', 'Языки'],
  ['physics', 'Физика'], ['chemistry', 'Химия'], ['biology', 'Биология'],
  ['history', 'История'], ['globe', 'География'], ['code', 'Программирование'],
  ['web', 'Веб-разработка'], ['terminal', 'Терминал'], ['game', 'Игры'],
  ['network', 'Алгоритмы'], ['robot', 'Робототехника'], ['exam', 'Экзамен'],
  ['oge', 'ОГЭ'], ['ielts', 'IELTS'], ['toefl', 'TOEFL'], ['hsk', 'HSK'],
  ['jlpt', 'JLPT'], ['dele', 'DELE'], ['target', 'Цель'],
]

const programmingFilters = [
  { label: 'Все направления', value: 'all' },
  { label: 'Python', value: 'python' },
  { label: 'Веб', value: 'web-development' },
  { label: 'Игры', value: 'unity-game-dev' },
  { label: 'Алгоритмы', value: 'algorithms' },
]

const languageFilters = [
  { label: 'Все экзамены', value: 'all' },
  { label: 'IELTS', value: 'english-ielts' },
  { label: 'TOEFL', value: 'toefl' },
  { label: 'HSK', value: 'hsk' },
  { label: 'JLPT', value: 'jlpt' },
  { label: 'DELE', value: 'dele' },
]

const reviewFilters = [
  { label: 'Все отзывы', value: 'all' },
  { label: 'ЕГЭ', value: 'ЕГЭ' },
  { label: 'ОГЭ', value: 'ОГЭ' },
  { label: 'Языки', value: 'IELTS' },
  { label: 'Программирование', value: 'IT' },
]

function App() {
  const [currentPath, setCurrentPath] = useState(getPath)
  const [subjects, setSubjects] = useState([])
  const [backendTeachers, setBackendTeachers] = useState([])
  const [session, setSession] = useState(loadStoredSession)

  useEffect(() => {
    const onPopState = () => setCurrentPath(getPath())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([fetchSubjects(), fetchTeachers()]).then(([subjectsResult, teachersResult]) => {
      if (cancelled) return
      if (subjectsResult.status === 'fulfilled') setSubjects(subjectsResult.value)
      if (teachersResult.status === 'fulfilled') setBackendTeachers(teachersResult.value)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const refreshTeachers = () => {
      fetchTeachers().then((teachers) => {
        if (!cancelled) setBackendTeachers(teachers)
      }).catch(() => {})
    }
    window.addEventListener('idioma:teachers-updated', refreshTeachers)
    return () => {
      cancelled = true
      window.removeEventListener('idioma:teachers-updated', refreshTeachers)
    }
  }, [])

  useEffect(() => {
    if (!session?.token) return
    getMe(session.token)
      .then((user) => saveSession({ token: session.token, user }, setSession))
      .catch(() => {
        window.localStorage.removeItem(SESSION_STORAGE_KEY)
        setSession(null)
      })
  }, [])

  const navigate = (href) => {
    const nextUrl = new URL(href, window.location.origin)
    const nextPath = nextUrl.pathname
    const nextSearch = nextUrl.search
    const nextHash = nextUrl.hash
    window.history.pushState({}, '', `${nextPath}${nextSearch}${nextHash}`)
    setCurrentPath(nextPath)

    if (nextHash) {
      requestAnimationFrame(() => document.querySelector(nextHash)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const handleAuthSuccess = (payload) => {
    saveSession(payload, setSession)
    navigate('/')
  }

  const handleLogout = () => {
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
    setSession(null)
    navigate('/')
  }

  const handleSessionUpdate = (userPatch) => {
    if (!session) return
    saveSession({ ...session, user: { ...session.user, ...userPatch } }, setSession)
  }

  const data = createPageData(subjects, backendTeachers)
  const Page = routes[currentPath] ?? HomePage
  const isDashboard = currentPath === '/dashboard'

  return (
    <div className={isDashboard ? 'app app--dashboard' : 'app'}>
      <Header currentPath={currentPath} onNavigate={navigate} session={session} onLogout={handleLogout} />
      <main>
        <Page onNavigate={navigate} data={data} session={session} onAuthSuccess={handleAuthSuccess} onSessionUpdate={handleSessionUpdate} />
      </main>
      {!isDashboard && <Footer onNavigate={navigate} />}
    </div>
  )
}

function loadStoredSession() {
  try {
    return JSON.parse(window.localStorage.getItem(SESSION_STORAGE_KEY))
  } catch {
    return null
  }
}

function saveSession(payload, setSession) {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload))
  setSession(payload)
}

function createPageData(subjects, backendTeachers) {
  const hasBackendSubjects = subjects.length > 0
  const courseCards = hasBackendSubjects ? subjects.map(subjectToCourseCard) : fallbackCourseCards.map(normalizeCourseCard)
  const examSubjects = hasBackendSubjects
    ? subjects.filter((subject) => subject.category === 'exams').map(subjectToSubjectCard)
    : fallbackExamSubjects.map(normalizeSubjectCard)
  const programmingTracks = hasBackendSubjects
    ? subjects.filter((subject) => subject.category === 'programming').map(subjectToTrackCard)
    : fallbackProgrammingTracks.map(normalizeTrackCard)
  const languageExams = hasBackendSubjects
    ? subjects.filter((subject) => subject.category === 'international' || subject.category === 'languages').map(subjectToTrackCard)
    : fallbackLanguageExams.map(normalizeTrackCard)
  // Keep the shape of API and fallback teachers identical.  In particular,
  // the API response does not include the derived `searchText` field, so
  // skipping normalization made subject names invisible to the local search.
  const teachers = backendTeachers.length > 0 ? backendTeachers.map(normalizeTeacher) : fallbackTeachers.map(normalizeTeacher)

  return { courseCards, examSubjects, programmingTracks, languageExams, teachers, subjects }
}

function subjectToCourseCard(subject) {
  return {
    slug: subject.slug,
    title: localizeExamText(subject.title),
    tag: subject.exam_type ? formatExamType(subject.exam_type) : categoryLabels[subject.category] ?? 'Предмет',
    subtitle: localizeExamText(subject.description),
    price: formatPrice(subject.price_month),
    icon: subject.icon,
    tint: subject.tint || 'peach',
    category: subject.category,
    examType: subject.exam_type,
    searchText: `${subject.title} ${subject.description}`,
  }
}

function subjectToSubjectCard(subject) {
  return {
    slug: subject.slug,
    title: localizeExamText(subject.title).replace(/ ЕГЭ| ОГЭ/g, ''),
    subtitle: localizeExamText(subject.description),
    price: formatPrice(subject.price_month),
    icon: subject.icon,
    category: subject.category,
    examType: subject.exam_type,
    searchText: `${subject.title} ${subject.description}`,
  }
}

function subjectToTrackCard(subject) {
  return {
    slug: subject.slug,
    title: localizeExamText(subject.title),
    text: localizeExamText(subject.description),
    price: formatPrice(subject.price_month),
    icon: subject.icon,
    category: subject.category,
    examType: subject.exam_type,
    searchText: `${subject.title} ${subject.description}`,
  }
}

function normalizeCourseCard(course) {
  const title = localizeExamText(course.title)
  const tag = localizeExamText(course.tag)
  const subtitle = localizeExamText(course.subtitle)
  return {
    ...course,
    title,
    tag,
    subtitle,
    slug: course.slug ?? fallbackSubjectSlug(course),
    price: formatPrice(course.price),
    category: course.icon === 'game' || course.icon === 'code' || course.icon === 'web' ? 'programming' : 'exams',
    examType: course.tag === 'ОГЭ' ? 'oge' : course.tag === 'ЕГЭ' ? 'ege' : null,
    searchText: `${title} ${subtitle} ${tag}`,
  }
}

function normalizeSubjectCard(subject) {
  const title = localizeExamText(subject.title)
  const subtitle = localizeExamText(subject.subtitle)
  return { ...subject, title, subtitle, slug: subject.slug ?? fallbackSubjectSlug(subject), price: formatPrice(subject.price), category: 'exams', searchText: `${title} ${subtitle}` }
}

function normalizeTrackCard(track) {
  const title = localizeExamText(track.title)
  const text = localizeExamText(track.text)
  return { ...track, title, text, price: formatPrice(track.price), slug: track.slug ?? fallbackSubjectSlug(track), searchText: `${title} ${text}` }
}

const fallbackSubjectSlugs = {
  sum: 'matematika-ege',
  code: 'informatika-oge',
  language: 'russkiy-ege',
  history: 'obschestvo-ege',
  physics: 'fizika-school',
  biology: 'biologiya-school',
  ielts: 'english-ielts',
  certificate: 'english-ielts',
  toefl: 'toefl',
  hsk: 'hsk',
  jlpt: 'jlpt',
  dele: 'dele',
  python: 'python',
  web: 'web-development',
  game: 'unity-game-dev',
  network: 'algorithms',
}

function fallbackSubjectSlug(item) {
  return fallbackSubjectSlugs[item.icon] ?? slugify(item.title)
}

function normalizeTeacher(teacher) {
  const subjects = Array.isArray(teacher.subjects)
    ? teacher.subjects.map((subject) => ({ ...subject, title: localizeExamText(subject.title) }))
    : []
  const categories = Array.isArray(teacher.categories)
    ? teacher.categories
    : (teacher.category ? [teacher.category] : [])
  const subjectText = subjects.flatMap((subject) => [
    subject.title,
    subject.slug?.replace(/[-_]/g, ' '),
    subject.category,
    subject.exam_type ?? subject.examType,
    subject.icon,
  ])
  const searchText = [
    teacher.name,
    teacher.full_name,
    teacher.role,
    teacher.description,
    teacher.subject_title,
    teacher.subject_slug?.replace(/[-_]/g, ' '),
    teacher.category,
    ...categories,
    ...subjectText,
  ].filter(Boolean).join(' ')
  return { ...teacher, subject_title: localizeExamText(teacher.subject_title), subjects, categories, category: teacher.category ?? categories[0] ?? 'all', searchText }
}

function localizeExamText(value) {
  return String(value ?? '').replace(/\bEGE\b/gi, 'ЕГЭ').replace(/\bOGE\b/gi, 'ОГЭ')
}

function formatExamType(value) {
  const normalized = String(value ?? '').toLowerCase()
  if (normalized === 'ege') return 'ЕГЭ'
  if (normalized === 'oge') return 'ОГЭ'
  return localizeExamText(value).toUpperCase()
}

function openSubjectTeachers(onNavigate, subject) {
  if (!subject?.slug) return
  onNavigate(`/teachers?subject=${encodeURIComponent(subject.slug)}`)
}

function formatPrice() {
  // Предметы продаются через запись к преподавателю: на витрине показываем
  // единый минимальный ориентир.
  return 'от 700 ₽ / мес.'
}

function slugify(value) {
  return value.toLowerCase().replace(/[^a-zа-яё0-9]+/gi, '-').replace(/^-|-$/g, '')
}

function matchesText(item, query) {
  const normalize = (value) => String(value ?? '')
    .normalize('NFKC')
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/[^a-zа-я0-9]+/gi, ' ')
    .trim()
  const queryTokens = normalize(query).split(/\s+/).filter(Boolean)
  if (queryTokens.length === 0) return true
  const haystack = normalize(item.searchText ?? `${item.title ?? ''} ${item.name ?? ''} ${item.role ?? ''} ${item.text ?? ''} ${item.subject_title ?? ''} ${item.subject_slug ?? ''}`)
  // Match every entered word independently, making searches such as
  // "математика егэ" tolerant to punctuation and word order.
  return queryTokens.every((token) => haystack.includes(token))
}

function matchesCatalogFilter(item, active) {
  if (!active || active === 'all') return true
  if (active === 'ege' || active === 'oge') return item.examType === active || (item.subjects ?? []).some((subject) => subject.exam_type === active || subject.examType === active)
  return item.category === active || (item.categories ?? []).includes(active)
}

function matchesSlugFilter(item, active) {
  if (!active || active === 'all') return true
  return item.slug === active || item.icon === active || item.title.toLowerCase().includes(active.replaceAll('-', ' '))
}

function getInitials(name = '') {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  return initials || 'ID'
}

function SmartLink({ href, className, children, onNavigate, ...props }) {
  const handleClick = (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
    event.preventDefault()
    onNavigate(href)
  }
  return <a href={href} className={className} onClick={handleClick} {...props}>{children}</a>
}

function Header({ currentPath, onNavigate, session, onLogout }) {
  const user = session?.user
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const openPage = (href) => {
    setIsUserMenuOpen(false)
    setIsMobileMenuOpen(false)
    onNavigate(href)
  }

  return (
    <header className="header">
      <div className="container header__inner">
        <Logo onClick={() => openPage('/')} />
        <nav className="header__nav" aria-label="Основная навигация">
          {navItems.map((item) => (
            <SmartLink key={item.href} href={item.href} onNavigate={onNavigate} className={currentPath === item.href ? 'is-active' : ''}>
              {item.label}
            </SmartLink>
          ))}
        </nav>
        <div className="header__actions">
          {!user && <SmartLink href="/teachers" onNavigate={onNavigate} className="button button--primary button--small">Начать бесплатно</SmartLink>}
          {user ? (
            <div className="user-menu">
              <button
                className="user-chip"
                type="button"
                title={user.full_name}
                aria-expanded={isUserMenuOpen}
                onClick={() => {
                  setIsUserMenuOpen((value) => !value)
                  setIsMobileMenuOpen(false)
                }}
              >
                {getInitials(user.full_name)}
              </button>
              {isUserMenuOpen && (
                <div className="user-menu__dropdown">
                  <button type="button" onClick={() => openPage('/dashboard')}>Личный кабинет</button>
                  <button type="button" onClick={() => { setIsUserMenuOpen(false); onLogout() }}>Выйти</button>
                </div>
              )}
            </div>
          ) : (
            <SmartLink href="/login" onNavigate={onNavigate} className="button button--ghost button--small header-login-link">Войти</SmartLink>
          )}
          <button
            className={`mobile-menu-toggle${isMobileMenuOpen ? ' is-open' : ''}`}
            type="button"
            aria-label={isMobileMenuOpen ? 'Закрыть меню' : 'Открыть меню'}
            aria-expanded={isMobileMenuOpen}
            onClick={() => setIsMobileMenuOpen((value) => !value)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>
      {isMobileMenuOpen && (
        <div className="mobile-menu" role="menu">
          <div className="mobile-menu__heading">Направления</div>
          {navItems.map((item) => (
            <SmartLink key={item.href} href={item.href} onNavigate={openPage} className={currentPath === item.href ? 'is-active' : ''}>
              {item.label}
            </SmartLink>
          ))}
          {user ? (
            <SmartLink href="/dashboard" onNavigate={openPage}>Личный кабинет</SmartLink>
          ) : (
            <>
              <SmartLink href="/teachers" onNavigate={openPage}>Начать бесплатно</SmartLink>
            </>
          )}
        </div>
      )}
    </header>
  )
}
function HomePage({ onNavigate, data, session }) {
  return (
    <>
      <Hero onNavigate={onNavigate} />
      <StatsBar />
      <DirectionsSection onNavigate={onNavigate} />
      <CoursesSection courses={data.courseCards.slice(0, 5)} onCourseSelect={(subject) => openSubjectTeachers(onNavigate, subject)} />
      <WhySection />
      <WorkflowSection />
      <TeachersAndReviews onNavigate={onNavigate} teachers={data.teachers} />
      <PricingSection onNavigate={onNavigate} />
      <FinalCta onNavigate={onNavigate} />
    </>
  )
}

function Hero({ onNavigate }) {
  return (
    <section className="hero">
      <div className="container hero__grid">
        <div className="hero__content reveal">
          <p className="eyebrow">idioma · онлайн-школа</p>
          <h1>Онлайн-школа для <span>учёбы, экзаменов</span> и будущей карьеры.</h1>
          <p className="hero__lead">Школьные предметы, подготовка к ЕГЭ и ОГЭ, иностранные языки и IT-направления в одном личном кабинете.</p>
          <div className="hero__actions">
            <SmartLink href="/teachers" onNavigate={onNavigate} className="button button--primary">Начать бесплатно <span aria-hidden="true">→</span></SmartLink>
            <SmartLink href="/catalog" onNavigate={onNavigate} className="button button--secondary">Смотреть направления</SmartLink>
          </div>
        </div>
        <div className="hero__visual" aria-label="Красная панда idioma за ноутбуком">
          <div className="hero__orb" />
          <RedPanda variant="laptop" className="hero__panda" />
          <FloatingCard className="card--exam" icon="exam" title="ЕГЭ и ОГЭ" text="подготовка к экзаменам" />
          <FloatingCard className="card--school" icon="books" title="Школьные предметы" text="5-11 классы" />
          <FloatingCard className="card--code" icon="code" title="Разработка и IT" text="от новичка до профи" />
        </div>
      </div>
    </section>
  )
}

function FloatingCard({ className, icon, title, text }) {
  return (
    <div className={`floating-card ${className}`}>
      <Icon name={icon} />
      <div><b>{title}</b><span>{text}</span></div>
    </div>
  )
}

function StatsBar() {
  return (
    <section className="container stats-bar" aria-label="Показатели школы">
      {stats.map((item) => (
        <article key={item.label} className="stat-item"><Icon name={item.icon} /><strong>{item.value}</strong><span>{item.label}</span></article>
      ))}
    </section>
  )
}

function SectionHeading({ kicker, title, action, onNavigate }) {
  return (
    <div className="section-heading">
      <div>{kicker && <p className="eyebrow">{kicker}</p>}<h2>{title}</h2></div>
      {action && <SmartLink href={action.href} onNavigate={onNavigate} className="section-link">{action.label}<span aria-hidden="true">→</span></SmartLink>}
    </div>
  )
}

function DirectionsSection({ onNavigate }) {
  return (
    <section className="container section">
      <SectionHeading title="Направления обучения" action={{ label: 'Все направления', href: '/catalog' }} onNavigate={onNavigate} />
      <div className="direction-grid">
        {directions.map((direction) => (
          <SmartLink key={direction.title} href={direction.href} onNavigate={onNavigate} className="direction-card">
            <Icon name={direction.icon} /><h3>{direction.title}</h3><p>{direction.description}</p>
          </SmartLink>
        ))}
      </div>
    </section>
  )
}

function CoursesSection({ courses, onCourseSelect }) {
  return <section className="container section section--tight"><SectionHeading title="Популярные предметы" /><CourseGrid courses={courses} onCourseSelect={onCourseSelect} /></section>
}

function CourseGrid({ courses, onCourseSelect }) {
  return (
    <div className="course-grid">
      {courses.map((course) => (
        <article key={course.slug ?? course.title} className={`course-card course-card--${course.tint ?? 'peach'}`} role="button" tabIndex="0" onClick={() => onCourseSelect?.(course)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onCourseSelect?.(course) } }}>
          <span className="course-card__tag">{course.tag}</span>
          <Icon name={course.icon} />
          <h3>{course.title}</h3>
          <p>{course.subtitle}</p>
          <div className="course-card__footer"><b>{course.price}</b><button type="button" aria-label={`Показать преподавателей по предмету ${course.title}`} onClick={(event) => { event.stopPropagation(); onCourseSelect?.(course) }}>→</button></div>
        </article>
      ))}
    </div>
  )
}

function CourseRequestModal({ course, session, onClose }) {
  const [form, setForm] = useState(() => ({
    contactMethod: 'telegram',
    contactValue: session?.user?.telegram_username ? `@${session.user.telegram_username}` : '',
    contactName: session?.user?.full_name ?? '',
  }))
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const description = course.subtitle || course.text || 'Предмет idioma с преподавателем и личным расписанием.'
  const contactPlaceholders = {
    telegram: '@username или номер телефона',
    max: 'ID, username или номер телефона',
    phone: '+7 999 000-00-00',
    email: 'name@example.com',
  }
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!course.slug) {
      setError('Для записи нужен предмет из базы данных. Обновите страницу или запустите backend.')
      return
    }
    if (!form.contactName.trim() || !form.contactValue.trim()) {
      setError('Заполните имя и контакт для связи')
      return
    }
    setStatus('loading')
    setError('')
    try {
      await createCourseRequest(session?.token, {
        subject_slug: course.slug,
        teacher_id: course.teacher_id ?? null,
        contact_name: form.contactName.trim(),
        contact_method: form.contactMethod,
        contact_value: form.contactValue.trim(),
        note: null,
      })
      setStatus('success')
    } catch (requestError) {
      setError(requestError.message)
      setStatus('error')
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <article className="course-request-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button className="user-modal__close" type="button" onClick={onClose}>×</button>
        <span className="course-card__tag">{course.tag || 'Предмет'}</span>
        <Icon name={course.icon || 'book'} size={44} />
        <h2>{course.title}</h2>
        <p>{description}</p>
        {course.price && <strong>{course.price}</strong>}
        {status === 'success' ? (
          <div className="course-request-modal__success">
            <b>Заявка отправлена</b>
            <span>Администратор увидит её в личном кабинете и свяжется с вами выбранным способом.</span>
            <button className="button button--primary" type="button" onClick={onClose}>Готово</button>
          </div>
        ) : (
          <form className="course-request-form" onSubmit={handleSubmit}>
            <label><span>Как с вами связаться</span><select value={form.contactMethod} onChange={update('contactMethod')}><option value="telegram">Telegram</option><option value="max">MAX</option><option value="phone">Номер телефона</option><option value="email">Почта</option></select></label>
            <label><span>Контакт</span><input value={form.contactValue} onChange={update('contactValue')} placeholder={contactPlaceholders[form.contactMethod]} required /></label>
            <label><span>Ваше имя</span><input value={form.contactName} onChange={update('contactName')} placeholder="Как к вам обращаться" required /></label>
            {error && <p className="form-error">{error}</p>}
            <button className="button button--primary" type="submit" disabled={status === 'loading'}>{status === 'loading' ? 'Отправляем…' : 'Отправить заявку'}</button>
          </form>
        )}
      </article>
    </div>
  )
}

function TeacherApplicationModal({ session, onClose }) {
  const [form, setForm] = useState(() => ({
    name: session?.user?.full_name ?? '',
    contactMethod: 'telegram',
    contactValue: session?.user?.telegram_username ? `@${session.user.telegram_username}` : '',
    subjects: '',
    note: '',
  }))
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const contactPlaceholders = {
    telegram: '@username или номер телефона',
    max: 'ID, username или номер телефона',
    phone: '+7 999 000-00-00',
    email: 'name@example.com',
  }
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.name.trim() || !form.contactValue.trim() || !form.subjects.trim()) {
      setError('Заполните имя, контакт и предметы')
      return
    }
    setStatus('loading')
    setError('')
    try {
      await createTeacherApplication({
        name: form.name.trim(),
        contact_method: form.contactMethod,
        contact_value: form.contactValue.trim(),
        subjects: form.subjects.trim(),
        note: form.note.trim() || null,
      })
      setStatus('success')
    } catch (requestError) {
      setError(requestError.message)
      setStatus('error')
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <article className="course-request-modal teacher-application-modal" role="dialog" aria-modal="true" aria-labelledby="teacher-application-title" onClick={(event) => event.stopPropagation()}>
        <button className="user-modal__close" type="button" aria-label="Закрыть" onClick={onClose}>×</button>
        <span className="course-card__tag">Работа в idioma</span>
        <Icon name="graduation" size={44} />
        <h2 id="teacher-application-title">Хочу преподавать</h2>
        <p>Оставьте контакты и расскажите, какие предметы хотите вести. Администратор свяжется с вами.</p>
        {status === 'success' ? (
          <div className="course-request-modal__success">
            <b>Заявка отправлена</b>
            <span>Администратор увидит её в личном кабинете и свяжется с вами выбранным способом.</span>
            <button className="button button--primary" type="button" onClick={onClose}>Готово</button>
          </div>
        ) : (
          <form className="course-request-form" onSubmit={handleSubmit}>
            <label><span>Ваше имя</span><input value={form.name} onChange={update('name')} placeholder="Как к вам обращаться" required /></label>
            <label><span>Как с вами связаться</span><select value={form.contactMethod} onChange={update('contactMethod')}><option value="telegram">Telegram</option><option value="max">MAX</option><option value="phone">Номер телефона</option><option value="email">Почта</option></select></label>
            <label><span>Контакт</span><input value={form.contactValue} onChange={update('contactValue')} placeholder={contactPlaceholders[form.contactMethod]} required /></label>
            <label><span>Какие предметы вы преподаёте</span><input value={form.subjects} onChange={update('subjects')} placeholder="Например: математика, физика, ЕГЭ" required /></label>
            <label><span>Опыт и комментарий</span><textarea value={form.note} onChange={update('note')} placeholder="Коротко расскажите об опыте преподавания" /></label>
            {error && <p className="form-error">{error}</p>}
            <button className="button button--primary" type="submit" disabled={status === 'loading'}>{status === 'loading' ? 'Отправляем…' : 'Отправить заявку'}</button>
          </form>
        )}
      </article>
    </div>
  )
}

function WhySection() {
  const items = [
    ['graduation', 'Сильные преподаватели', 'Эксперты ЕГЭ, языков и IT помогают двигаться без хаоса.'],
    ['profile', 'Персональный план', 'Подбираем понятный маршрут занятий под вашу цель.'],
    ['play', 'Живые занятия', 'Практика, разбор ошибок и обратная связь после уроков.'],
    ['calendar', 'Гибкий график', 'Учись в удобное время и не теряй прогресс.'],
    ['chart', 'Аналитика прогресса', 'Личный кабинет показывает баллы, дедлайны и рекомендации.'],
  ]
  return (
    <section className="container section section--tight">
      <SectionHeading title={<>Почему выбирают <span className="accent">idioma</span></>} />
      <div className="why-grid">{items.map(([icon, title, text]) => <article key={title} className="why-card"><Icon name={icon} /><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>
  )
}

function WorkflowSection() {
  return (
    <section className="container section process-section">
      <div className="workflow">
        <h2>Как это работает</h2>
        <div className="workflow__steps">
          {workflowSteps.map((step, index) => (
            <article key={step.title} className="workflow-step"><span className="workflow-step__number">{String(index + 1).padStart(2, '0')}</span><Icon name={step.icon} /><h3>{step.title}</h3><p>{step.text}</p></article>
          ))}
        </div>
      </div>
    </section>
  )
}

function TeachersAndReviews({ onNavigate, teachers }) {
  return (
    <section className="container section section--teachers">
      <div className="teacher-band">
        <div className="teacher-band__intro"><h2>Преподаватели и ученики</h2><p>Наши учителя — эксперты в своих предметах и наставники, которые помогают не потеряться по дороге к результату.</p><SmartLink href="/teachers" onNavigate={onNavigate} className="button button--dark">Смотреть всех преподавателей</SmartLink></div>
        <div className="teacher-cards">{teachers.slice(0, 3).map((teacher) => <TeacherCard key={teacher.id ?? teacher.name} teacher={teacher} compact />)}</div>
        <div className="review-score"><h3>Отзывы учеников</h3><strong>4.9</strong><span>на основе 2300+ отзывов</span><SmartLink href="/reviews" onNavigate={onNavigate} className="button button--secondary">Читать отзывы</SmartLink></div>
      </div>
    </section>
  )
}

function TeacherCard({ teacher, compact = false, onSelect }) {
  const hourlyPrice = Number(teacher.lesson_price ?? teacher.lessonPrice ?? 0)
  return (
    <article className={compact ? 'teacher-card teacher-card--compact' : 'teacher-card'}>
      <div className="teacher-card__avatar" aria-hidden="true">{teacher.avatar_url || teacher.avatarUrl ? <img src={teacher.avatar_url || teacher.avatarUrl} alt="" /> : teacher.initials}</div>
      <h3>{teacher.name}</h3><p className="teacher-card__role">{teacher.role}</p><p className="teacher-card__description">{teacher.description}</p>
      <div className="teacher-card__meta">
        {!compact && <div className="teacher-card__subjects">{(teacher.subjects ?? []).map((subject) => <span key={subject.slug}><Icon name={subject.icon || 'book'} size={16} />{subject.title}</span>)}</div>}
        <div className="teacher-card__footer">
          <div className="teacher-card__rating" aria-label={`Отзывы и рейтинг ${Number(teacher.rating).toFixed(1)} из 5`}><span>★★★★★</span><b>{Number(teacher.rating).toFixed(1)}</b></div>
          {!compact && <strong className="teacher-card__price">{hourlyPrice > 0 ? `${hourlyPrice.toLocaleString('ru-RU')} ₽ / час` : 'Цена по запросу'}</strong>}
        </div>
        {!compact && onSelect && <button className="button button--primary teacher-card__action" type="button" onClick={onSelect}>Записаться к преподавателю</button>}
      </div>
    </article>
  )
}

function PricingSection({ onNavigate }) {
  return (
    <section className="container section">
      <SectionHeading title="Стоимость занятий" action={{ label: 'Выбрать преподавателя', href: '/teachers' }} onNavigate={onNavigate} />
      <div className="pricing-grid">
        {pricingPlans.map((plan) => (
          <article key={plan.name} className={plan.popular ? 'price-card price-card--popular' : 'price-card'}>
            {plan.popular && <span className="popular-label">Популярный</span>}<h3>{plan.name}</h3><p>{plan.description}</p><strong>{plan.price}</strong>
            <ul>{plan.features.map((feature) => <li key={feature}>{feature}</li>)}</ul>
            <SmartLink href="/teachers" onNavigate={onNavigate} className="button button--secondary">Выбрать преподавателя</SmartLink>
          </article>
        ))}
      </div>
    </section>
  )
}

function FinalCta({ onNavigate }) {
  return (
    <section className="container final-cta">
      <div><h2>Готовы к новым достижениям?</h2><p>Начните бесплатно уже сегодня и получите персональный план.</p></div>
      <SmartLink href="/teachers" onNavigate={onNavigate} className="button button--primary">Начать бесплатно</SmartLink>
      <RedPanda variant="books" className="final-cta__panda" />
    </section>
  )
}
function CatalogPage({ onNavigate, data, session }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [query, setQuery] = useState('')
  const customCategories = [...new Set(data.subjects.map((subject) => subject.category).filter(Boolean))]
    .filter((category) => !catalogFilters.some((filter) => filter.value === category))
  const categoryFilters = [
    ...catalogFilters,
    ...customCategories.map((category) => ({ label: categoryLabels[category] ?? category, value: category })),
  ]
  const filteredCourses = data.courseCards.filter((course) => matchesCatalogFilter(course, activeFilter) && matchesText(course, query))

  return (
    <PageShell>
      <PageHero kicker="Каталог" title="Каталог предметов" text="Выберите предмет и начните учиться с комфортом вместе с idioma." panda="book" />
      <CourseFilters labels={categoryFilters} active={activeFilter} query={query} onActiveChange={setActiveFilter} onQueryChange={setQuery} />
      <CourseGrid courses={filteredCourses} onCourseSelect={(subject) => openSubjectTeachers(onNavigate, subject)} />
      <MiniStats />
      <DarkCta onNavigate={onNavigate} title="Не знаете, с чего начать?" text="Начните бесплатно и получите рекомендации по обучению." />
    </PageShell>
  )
}

function ExamsPage({ onNavigate, data, session }) {
  const [examType, setExamType] = useState('ege')
  const subjects = data.examSubjects.filter((subject) => !subject.examType || subject.examType === examType)

  return (
    <PageShell>
      <PageHero kicker="ЕГЭ и ОГЭ" title="Подготовка к ЕГЭ и ОГЭ" text="Системная подготовка, актуальные материалы и поддержка на каждом этапе." panda="laptop">
        <ul className="hero-list"><li>Актуальные программы и материалы 2026 года</li><li>Пробники, разбор ошибок и контроль динамики баллов</li><li>Персональный план подготовки</li></ul>
      </PageHero>
      <ToggleTabs items={[{ label: 'ЕГЭ', value: 'ege' }, { label: 'ОГЭ', value: 'oge' }]} active={examType} onChange={setExamType} />
      <SectionHeading title="Выберите предмет" />
      <SubjectGrid subjects={subjects} onSubjectSelect={(subject) => openSubjectTeachers(onNavigate, subject)} />
      <SectionHeading title="Пробные экзамены" />
      <div className="exam-card-grid">
        {['Пробный экзамен', 'Мини-тест', 'Разбор ошибок'].map((title, index) => (
          <article key={title} className="exam-card"><Icon name={index === 1 ? 'document' : 'exam'} /><h3>{title}</h3><p>{index === 2 ? 'Разберём сложные задания и составим план подготовки.' : 'Проверьте знания в формате реального экзамена.'}</p><b>{index === 2 ? 'Бесплатно' : `от ${index === 0 ? '790' : '490'} ₽`}</b></article>
        ))}
      </div>
      <DarkCta onNavigate={onNavigate} title="Готовы сдать экзамен на максимум?" text="Подберём предмет и преподавателя, а затем составим план подготовки под вашу цель." />
    </PageShell>
  )
}

function ProgrammingPage({ onNavigate, data, session }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [query, setQuery] = useState('')
  const tracks = data.programmingTracks.filter((track) => matchesSlugFilter(track, activeFilter) && matchesText(track, query))

  return (
    <PageShell>
      <PageHero kicker="Программирование и IT" title="Программирование и IT" text="Практические занятия по программированию, разработке игр и современным IT-профессиям." panda="code">
        <ul className="hero-list"><li>От основ до продвинутого уровня</li><li>Проекты для портфолио</li><li>Практика и проверка кода преподавателем</li></ul>
      </PageHero>
      <CourseFilters labels={programmingFilters} active={activeFilter} query={query} onActiveChange={setActiveFilter} onQueryChange={setQuery} />
      <SectionHeading title="Направления обучения" />
      <TrackGrid tracks={tracks} onTrackSelect={(subject) => openSubjectTeachers(onNavigate, subject)} />
      <MiniStats />
      <DarkCta onNavigate={onNavigate} title="Определим подходящий путь обучения" text="Выберите преподавателя и получите рекомендации по программе занятий." />
    </PageShell>
  )
}

function LanguagesPage({ onNavigate, data, session }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [query, setQuery] = useState('')
  const exams = data.languageExams.filter((exam) => matchesSlugFilter(exam, activeFilter) && matchesText(exam, query))

  return (
    <PageShell>
      <PageHero kicker="Языки" title="Иностранные языки и международные экзамены" text="Подготовка к IELTS, TOEFL, HSK, JLPT, DELE и уверенная языковая практика для жизни, учёбы и работы." panda="globe">
        <ul className="hero-list"><li>Опытные преподаватели-практики</li><li>Разговорная практика и грамматика без перегруза</li><li>Индивидуальный план подготовки</li></ul>
      </PageHero>
      <CourseFilters labels={languageFilters} active={activeFilter} query={query} onActiveChange={setActiveFilter} onQueryChange={setQuery} />
      <SectionHeading title="Выберите экзамен" />
      <TrackGrid tracks={exams} onTrackSelect={(subject) => openSubjectTeachers(onNavigate, subject)} />
      <DarkCta onNavigate={onNavigate} title="Не знаете, какой экзамен вам нужен?" text="Подберём формат и темп подготовки под вашу цель." />
    </PageShell>
  )
}

function SubjectFilterSelect({ subjects, value, onChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef(null)
  const selectedSubject = subjects.find((subject) => subject.slug === value)
  const filteredSubjects = subjects.filter((subject) => matchesText({ searchText: `${subject.title} ${subject.description ?? ''}` }, query))

  useEffect(() => {
    if (!isOpen) return undefined
    const closeOnOutsideClick = (event) => {
      if (!rootRef.current?.contains(event.target)) setIsOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [isOpen])

  const selectSubject = (slug) => {
    onChange(slug)
    setIsOpen(false)
    setQuery('')
  }

  return (
    <div className={`subject-select${isOpen ? ' is-open' : ''}`} ref={rootRef}>
      <span className="subject-select__label">Предмет</span>
      <button className="subject-select__trigger" type="button" aria-haspopup="listbox" aria-expanded={isOpen} onClick={() => setIsOpen((current) => !current)}>
        <Icon name={selectedSubject?.icon || 'books'} size={22} />
        <span>{selectedSubject?.title || 'Все предметы'}</span>
        <i aria-hidden="true" />
      </button>
      {isOpen && (
        <div className="subject-select__menu">
          <label className="subject-select__search">
            <Icon name="search" size={20} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Найти предмет" />
          </label>
          <div className="subject-select__options" role="listbox" aria-label="Выбор предмета">
            {!query && (
              <button className={value === 'all' ? 'is-selected' : ''} type="button" role="option" aria-selected={value === 'all'} onClick={() => selectSubject('all')}>
                <Icon name="books" size={22} /><span>Все предметы</span>{value === 'all' && <Icon name="check" size={18} />}
              </button>
            )}
            {filteredSubjects.map((subject) => (
              <button key={subject.slug} className={value === subject.slug ? 'is-selected' : ''} type="button" role="option" aria-selected={value === subject.slug} onClick={() => selectSubject(subject.slug)}>
                <Icon name={subject.icon || 'book'} size={22} /><span>{subject.title}</span>{value === subject.slug && <Icon name="check" size={18} />}
              </button>
            ))}
            {filteredSubjects.length === 0 && <p>Ничего не найдено</p>}
          </div>
        </div>
      )}
    </div>
  )
}

function TeachersPage({ onNavigate, data, session }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [subjectFilter, setSubjectFilter] = useState(() => new URLSearchParams(window.location.search).get('subject') || 'all')
  const [priceFrom, setPriceFrom] = useState(0)
  const [priceTo, setPriceTo] = useState(TEACHER_PRICE_MAX)
  const [query, setQuery] = useState('')
  const [selectedTeacher, setSelectedTeacher] = useState(null)
  const [showTeacherApplication, setShowTeacherApplication] = useState(false)
  const customCategories = [...new Set(data.teachers.flatMap((teacher) => teacher.categories ?? []))]
    .filter((category) => !teacherFilters.some((filter) => filter.value === category))
  const categoryFilters = [
    ...teacherFilters,
    ...customCategories.map((category) => ({ label: categoryLabels[category] ?? category, value: category })),
  ]
  const teachers = data.teachers.filter((teacher) => {
    const byCategory = matchesCatalogFilter(teacher, activeFilter)
    const bySubject = subjectFilter === 'all' || (teacher.subjects ?? []).some((subject) => subject.slug === subjectFilter)
    const price = Number(teacher.lesson_price ?? teacher.lessonPrice ?? 0)
    const byPrice = price >= priceFrom && price <= priceTo
    return byCategory && bySubject && byPrice && matchesText(teacher, query)
  })

  return (
    <PageShell>
      <PageHero kicker="Первое занятие — бесплатно" title="Наши преподаватели" text="Опытные эксперты, которые помогут вам достичь целей легко и уверенно." panda="teacher" />
      <CourseFilters labels={categoryFilters} active={activeFilter} query={query} onActiveChange={setActiveFilter} onQueryChange={setQuery} />
      <div className="teacher-filters-extra">
        <SubjectFilterSelect subjects={data.subjects} value={subjectFilter} onChange={setSubjectFilter} />
        <div className="teacher-price-filter">
          <div className="teacher-price-filter__header"><span>Стоимость часа</span><b>{priceFrom.toLocaleString('ru-RU')}–{priceTo.toLocaleString('ru-RU')} ₽</b></div>
          <div className="teacher-price-filter__range" style={{ '--price-from': `${priceFrom / TEACHER_PRICE_MAX * 100}%`, '--price-to': `${priceTo / TEACHER_PRICE_MAX * 100}%` }}>
            <div className="teacher-price-filter__track" />
            <input aria-label="Минимальная стоимость часа" type="range" min="0" max={TEACHER_PRICE_MAX} step="100" value={priceFrom} onChange={(event) => setPriceFrom(Math.min(Number(event.target.value), priceTo))} />
            <input aria-label="Максимальная стоимость часа" type="range" min="0" max={TEACHER_PRICE_MAX} step="100" value={priceTo} onChange={(event) => setPriceTo(Math.max(Number(event.target.value), priceFrom))} />
          </div>
          <div className="teacher-price-filter__bounds">
            <span>От {priceFrom.toLocaleString('ru-RU')} ₽</span><span>До {priceTo.toLocaleString('ru-RU')} ₽</span>
          </div>
        </div>
      </div>
      <div className="teachers-grid">{teachers.map((teacher) => <TeacherCard key={teacher.id ?? teacher.name} teacher={teacher} onSelect={() => setSelectedTeacher(teacher)} />)}</div>
      <DarkCta onNavigate={onNavigate} title="Станьте частью команды idioma" text="Мы расширяем команду профессионалов. Если вы любите преподавать — напишите нам." action="Хочу преподавать" onAction={() => setShowTeacherApplication(true)} />
      {selectedTeacher && <CourseRequestModal course={{ slug: selectedTeacher.subject_slug || selectedTeacher.subjects?.[0]?.slug, title: selectedTeacher.name, tag: selectedTeacher.role, subtitle: selectedTeacher.description, icon: selectedTeacher.subjects?.[0]?.icon || 'book', teacher_id: selectedTeacher.id }} session={session} onClose={() => setSelectedTeacher(null)} onNavigate={onNavigate} />}
      {showTeacherApplication && <TeacherApplicationModal session={session} onClose={() => setShowTeacherApplication(false)} />}
    </PageShell>
  )
}

function ReviewsPage({ onNavigate }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [query, setQuery] = useState('')
  const filteredReviews = reviews.filter((review) => {
    const byFilter = activeFilter === 'all' || review.subject === activeFilter
    const byText = matchesText({ searchText: `${review.subject} ${review.name} ${review.title} ${review.text}` }, query)
    return byFilter && byText
  })

  return (
    <PageShell>
      <PageHero kicker="Отзывы" title="Отзывы учеников" text="Реальные истории, результаты и достижения наших студентов." panda="reading" />
      <CourseFilters labels={reviewFilters} active={activeFilter} query={query} onActiveChange={setActiveFilter} onQueryChange={setQuery} />
      <div className="reviews-grid">
        {filteredReviews.map((review) => (
          <article key={review.name} className="review-card"><span className="review-card__tag">{review.subject}</span><h3>{review.title}</h3><p>{review.text}</p><div><b>{review.name}</b><strong>{review.result}</strong></div></article>
        ))}
      </div>
      <DarkCta onNavigate={onNavigate} title="Хотите такой же результат?" text="Начните бесплатно — дальше мы соберём понятный маршрут." />
    </PageShell>
  )
}
function LoginPage({ onNavigate, session, onAuthSuccess }) {
  return <PageShell className="page-shell--auth"><div className="auth-layout auth-layout--page"><AuthCard session={session} onAuthSuccess={onAuthSuccess} onNavigate={onNavigate} /></div></PageShell>
}

function AuthCard({ session, onAuthSuccess, onNavigate }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ fullName: '', email: '', password: '' })
  const [statusMessage, setStatusMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const isRegister = mode === 'register'

  const updateField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    setStatusMessage('')
    setIsLoading(true)
    try {
      const payload = isRegister
        ? await register({ email: form.email, password: form.password, full_name: form.fullName })
        : await login({ email: form.email, password: form.password })
      onAuthSuccess(payload)
    } catch (error) {
      setStatusMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  if (session?.user) {
    return (
      <article className="auth-card auth-card--single">
        <RedPanda variant="auth" className="auth-card__panda" />
        <h1>Вы уже вошли</h1>
        <p className="auth-card__hint">{session.user.full_name}, аккаунт готов к работе. Можно перейти в личный кабинет или продолжить выбирать предметы.</p>
        <SmartLink href="/dashboard" onNavigate={onNavigate} className="button button--primary">Перейти в кабинет</SmartLink>
      </article>
    )
  }

  return (
    <article className="auth-card auth-card--single">
      <RedPanda variant="auth" className="auth-card__panda" />
      <div className={`auth-tabs ${isRegister ? 'is-register' : 'is-login'}`} role="tablist" aria-label="Авторизация">
        <button className={!isRegister ? 'is-active' : ''} type="button" onClick={() => setMode('login')}>Вход</button>
        <button className={`auth-tab--register${isRegister ? ' is-active' : ''}`} type="button" onClick={() => setMode('register')}>Регистрация</button>
      </div>
      <div className={`auth-mode-panel auth-mode-panel--${mode}`} key={mode}>
        <h1>{isRegister ? 'Создать аккаунт' : 'Вход в аккаунт'}</h1>
        <form onSubmit={handleSubmit}>
          {isRegister && <label>Имя<input value={form.fullName} onChange={updateField('fullName')} placeholder="Введите ваше имя" required /></label>}
          <label>Email<input value={form.email} onChange={updateField('email')} placeholder="Введите e-mail" type="email" required /></label>
          <label>Пароль<input value={form.password} onChange={updateField('password')} placeholder={isRegister ? 'Создайте пароль' : 'Введите пароль'} type="password" minLength={6} required /></label>
          {statusMessage && <p className="auth-message">{statusMessage}</p>}
          <button className="button button--primary" type="submit" disabled={isLoading}>{isLoading ? 'Проверяем...' : isRegister ? 'Зарегистрироваться' : 'Войти'}</button>
        </form>
        <p className="auth-card__hint">Социальные входы появятся позже</p>
        <div className="social-row" aria-label="Будущие способы входа"><span>G</span><span>VK</span><span>Я</span></div>
        <button className={`auth-switch${isRegister ? '' : ' auth-switch--register'}`} type="button" onClick={() => setMode(isRegister ? 'login' : 'register')}>{isRegister ? 'Уже есть аккаунт? Войти' : 'Ещё не зарегистрированы? Создать аккаунт'}</button>
      </div>
    </article>
  )
}
function DashboardPage(props) {
  if (props.session?.user?.role === 'admin') {
    return <AdminDashboardPage {...props} />
  }
  if (props.session?.user?.role === 'teacher') {
    return <TeacherDashboardPage {...props} />
  }
  return <StudentDashboardPage {...props} />
}
function StudentDashboardPage({ onNavigate, session, onSessionUpdate }) {
  const [activeTab, setActiveTab] = useState(() => getDashboardInitialTab(session?.user?.role))
  useResponsiveDashboardTabs(setActiveTab, 'student')
  const [dashboard, setDashboard] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!session?.token) {
      setStatus('guest')
      return
    }

    let cancelled = false
    setStatus('loading')
    fetchStudentDashboard(session.token)
      .then((payload) => {
        if (cancelled) return
        setDashboard(payload)
        setStatus('ready')
      })
      .catch((requestError) => {
        if (cancelled) return
        setError(requestError.message)
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [session?.token])

  if (status === 'guest') {
    return (
      <PageShell>
        <section className="dashboard-empty">
          <h1>Нужно войти в аккаунт</h1>
          <p>Личный кабинет открывается после авторизации.</p>
          <SmartLink href="/login" onNavigate={onNavigate} className="button button--primary">Войти</SmartLink>
        </section>
      </PageShell>
    )
  }

  if (status === 'loading') {
    return <div className="dashboard-loading">Загружаем личный кабинет...</div>
  }

  if (status === 'error') {
    return <div className="dashboard-loading dashboard-loading--error">{error || 'Не удалось загрузить личный кабинет'}</div>
  }

  const tabs = [
    { id: 'overview', label: 'Главная', icon: 'home' },
    { id: 'courses', label: 'Предметы', icon: 'books' },
    { id: 'schedule', label: 'Расписание', icon: 'calendar' },
    { id: 'achievements', label: 'Достижения', icon: 'chart' },
    { id: 'settings', label: 'Настройки', icon: 'settings' },
  ]

  return (
    <div className="student-dashboard-shell">
      <aside className="student-sidebar">
        <nav aria-label="Личный кабинет">
          {tabs.map((tab) => (
            <button key={tab.id} className={`${activeTab === tab.id ? 'is-active ' : ''}${['messages', 'schedule', 'settings'].includes(tab.id) ? '' : 'dashboard-tab--desktop-only'}`} type="button" onClick={() => setActiveTab(tab.id)}>
              <Icon name={tab.icon} />{tab.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="student-main">
        <DashboardTop dashboard={dashboard} />
        {activeTab === 'overview' && <DashboardOverview dashboard={dashboard} onTabChange={setActiveTab} />}
        {activeTab === 'courses' && <DashboardCoursesPage courses={dashboard.courses} />}
        {activeTab === 'schedule' && <DashboardSchedulePage lessons={dashboard.lessons} />}
        {activeTab === 'achievements' && <DashboardAchievementsPage achievements={dashboard.achievements} />}
        {activeTab === 'settings' && (
          <DashboardSettingsPage
            settings={dashboard.settings}
            token={session.token}
            onDashboardUpdate={setDashboard}
            onSessionUpdate={onSessionUpdate}
          />
        )}
      </section>
    </div>
  )
}

function DashboardTop({ dashboard }) {
  const streak = dashboard.summary.streak

  return (
    <div className="dashboard-topbar">
      <div>
        <p className="eyebrow">{dashboard.summary.eyebrow}</p>
        <h1>{dashboard.summary.greeting}</h1>
        <p>{dashboard.summary.text}</p>
      </div>
      <div className="dashboard-streak"><Icon name={streak.icon} /><b>{streak.value} {streak.unit}</b><span>{streak.label}</span></div>
    </div>
  )
}

function DashboardStats({ stats }) {
  return <div className="dashboard-stats">{stats.map((stat) => <article key={stat.id}><Icon name={stat.icon} /><b>{stat.value}</b><span>{stat.label}</span></article>)}</div>
}

function DashboardOverview({ dashboard, onTabChange }) {
  return (
    <>
      <DashboardStats stats={dashboard.stats} />
      <div className="dashboard-grid">
        <section className="dashboard-panel dashboard-panel--wide">
          <div className="dashboard-panel__header"><h2>Мои предметы</h2><button type="button" onClick={() => onTabChange('courses')}>Все предметы</button></div>
          <DashboardCourseList courses={dashboard.courses.slice(0, 3)} />
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-panel__header"><h2>Ближайшие занятия</h2><button type="button" onClick={() => onTabChange('schedule')}>Расписание</button></div>
          <DashboardLessonList lessons={dashboard.lessons.slice(0, 3)} />
        </section>

        <section className="dashboard-panel dashboard-panel--accent">
          <RedPanda variant={dashboard.recommendation.panda || 'trophy'} />
          <div><h2>{dashboard.recommendation.title}</h2><p>{dashboard.recommendation.text}</p>{dashboard.recommendation.button && dashboard.recommendation.button !== 'Начать бесплатно' && <button type="button">{dashboard.recommendation.button}</button>}</div>
        </section>
      </div>
    </>
  )
}
function DashboardCoursesPage({ courses }) {
  return <section className="dashboard-panel dashboard-panel--full"><div className="dashboard-panel__header"><h2>Предметы</h2></div><DashboardCourseList courses={courses} /></section>
}

function DashboardSchedulePage({ lessons, calendarSync }) {
  const [weekOffset, setWeekOffset] = useState(0)
  const week = buildDashboardWeek(lessons, weekOffset)
  const weekRange = formatDashboardWeekRange(week)

  return (
    <section className="dashboard-panel dashboard-panel--full dashboard-panel--schedule">
      <div className="dashboard-panel__header dashboard-panel__header--schedule">
        <div>
          <h2>Расписание</h2>
          <span>{weekRange}</span>
          {calendarSync?.configured && (
            <small className={`calendar-sync-status${calendarSync.status === 'error' ? ' is-error' : ''}`}>
              {calendarSync.status === 'error' ? `Google Calendar: ${calendarSync.message}` : 'Синхронизировано с Google Calendar'}
            </small>
          )}
        </div>
        <div className="schedule-calendar__nav" aria-label="Переключение недели">
          <button type="button" onClick={() => setWeekOffset((value) => value - 1)}>Назад</button>
          <button type="button" onClick={() => setWeekOffset(0)} disabled={weekOffset === 0}>Сегодня</button>
          <button type="button" onClick={() => setWeekOffset((value) => value + 1)}>Следующая неделя</button>
        </div>
      </div>
      <div className="schedule-calendar" aria-label="Расписание">
        {week.map((day) => (
          <article key={day.key} className={day.isToday ? 'is-today' : ''}>
            <header><span>{day.weekday}</span><b>{day.dayNumber}</b></header>
            <div className="schedule-calendar__lessons">
              {day.lessons.length > 0 ? day.lessons.map((lesson) => (
                <div key={`${day.key}-${lesson.id}`} className="schedule-calendar__lesson">
                  <time>{lesson.time}</time>
                  <strong>{lesson.course}</strong>
                  <span>{lesson.topic}</span>
                </div>
              )) : <p className="schedule-calendar__empty">Нет занятий</p>}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function buildDashboardWeek(lessons, weekOffset = 0) {
  const today = new Date()
  const monday = new Date(today)
  monday.setHours(0, 0, 0, 0)
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7) + weekOffset * 7)

  return ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((weekday, index) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + index)
    const dateKey = formatLocalDateKey(date)
    const dayLessons = lessons
      .filter((lesson) => lesson.date ? lesson.date === dateKey : Number(lesson.day_offset ?? 0) === index)
      .sort((left, right) => String(left.time).localeCompare(String(right.time)))

    return {
      key: dateKey,
      weekday,
      dayNumber: date.getDate(),
      monthNumber: date.getMonth() + 1,
      isToday: isSameCalendarDay(date, today),
      lessons: dayLessons,
    }
  })
}

function formatLocalDateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDashboardWeekRange(week) {
  if (!week.length) return ''
  const first = week[0]
  const last = week[week.length - 1]
  return `${first.dayNumber}.${String(first.monthNumber).padStart(2, '0')} - ${last.dayNumber}.${String(last.monthNumber).padStart(2, '0')}`
}

function isSameCalendarDay(left, right) {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth() && left.getDate() === right.getDate()
}
function DashboardAchievementsPage({ achievements }) {
  return <section className="dashboard-panel dashboard-panel--full"><div className="dashboard-panel__header"><h2>Достижения</h2></div><DashboardAchievementList achievements={achievements} /></section>
}

function DashboardSettingsPage({ settings, token, onDashboardUpdate, onSessionUpdate }) {
  const [form, setForm] = useState(() => buildSettingsForm(settings))
  const [statusMessage, setStatusMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setForm(buildSettingsForm(settings))
    setStatusMessage('')
  }, [settings])

  const updateField = (key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    setForm((current) => ({ ...current, [key]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsSaving(true)
    setStatusMessage('')

    try {
      const updatedDashboard = await updateStudentSettings(token, {
        full_name: form.fullName,
        notifications: form.notifications,
        weekly_digest: form.weeklyDigest,
        lesson_reminders: form.lessonReminders,
        timezone: form.timezone,
      })
      onDashboardUpdate(updatedDashboard)
      onSessionUpdate?.({ full_name: updatedDashboard.settings.profile.name })
      setStatusMessage('Настройки сохранены')
    } catch (error) {
      setStatusMessage(error.message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="dashboard-panel dashboard-panel--full dashboard-settings">
      <div className="dashboard-panel__header"><h2>Настройки</h2></div>
      <form className="settings-form" onSubmit={handleSubmit}>
        <div className="settings-profile-grid">
          <label className="settings-field">
            <Icon name="profile" />
            <span>Имя пользователя</span>
            <input value={form.fullName} onChange={updateField('fullName')} minLength={2} maxLength={140} required />
          </label>
          <label className="settings-field settings-field--readonly">
            <Icon name="document" />
            <span>Почта</span>
            <input value={form.email} readOnly />
          </label>
        </div>

        <div className="settings-list settings-list--editable">
          <SettingsToggle label="Уведомления" checked={form.notifications} onChange={updateField('notifications')} />
          <SettingsToggle label="Еженедельный отчет" checked={form.weeklyDigest} onChange={updateField('weeklyDigest')} />
          <SettingsToggle label="Напоминания о занятиях" checked={form.lessonReminders} onChange={updateField('lessonReminders')} />
          <label className="settings-control">
            <span>Часовой пояс</span>
            <select value={form.timezone} onChange={updateField('timezone')}>
              <option value="Europe/Moscow">Europe/Moscow</option>
              <option value="Europe/Samara">Europe/Samara</option>
              <option value="Asia/Yekaterinburg">Asia/Yekaterinburg</option>
              <option value="Asia/Novosibirsk">Asia/Novosibirsk</option>
              <option value="Asia/Vladivostok">Asia/Vladivostok</option>
            </select>
          </label>
        </div>

        <div className="settings-actions">
          {statusMessage && <p className="settings-message">{statusMessage}</p>}
          <button className="button button--primary" type="submit" disabled={isSaving}>{isSaving ? 'Сохраняем...' : 'Сохранить настройки'}</button>
        </div>
      </form>
    </section>
  )
}

function buildSettingsForm(settings) {
  return {
    fullName: settings.profile?.name ?? '',
    email: settings.profile?.email ?? '',
    notifications: Boolean(settings.notifications),
    weeklyDigest: Boolean(settings.weekly_digest),
    lessonReminders: Boolean(settings.lesson_reminders),
    timezone: settings.timezone ?? 'Europe/Moscow',
  }
}

function SettingsToggle({ label, checked, onChange }) {
  return (
    <label className="settings-control settings-control--toggle">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <i aria-hidden="true" />
      <b>{checked ? 'Включено' : 'Выключено'}</b>
    </label>
  )
}

function DashboardCourseList({ courses }) {
  if (courses.length === 0) return <p className="dashboard-list-empty">Пока нет предметов</p>

  return (
    <div className="dashboard-course-list">
      {courses.map((course) => (
        <article key={course.slug ?? course.id}>
          <Icon name={course.icon} />
          <div><h3>{course.title}</h3><p>{course.subtitle}</p><span><i style={{ width: `${course.progress}%` }} /></span></div>
          <b>{course.progress}%</b>
        </article>
      ))}
    </div>
  )
}

function DashboardLessonList({ lessons }) {
  if (lessons.length === 0) return <p className="dashboard-list-empty">Пока нет занятий</p>

  return <ul className="lesson-list">{lessons.map((lesson) => <li key={lesson.id}><time>{lesson.time}</time><div><b>{lesson.course}</b><span>{lesson.topic}</span></div><mark>{lesson.status}</mark></li>)}</ul>
}

function DashboardAchievementList({ achievements }) {
  if (achievements.length === 0) return <p className="dashboard-list-empty">Пока нет достижений</p>

  return (
    <div className="achievement-list">
      {achievements.map((achievement) => (
        <article key={achievement.id}>
          <Icon name={achievement.icon} />
          <div><h3>{achievement.title}</h3><p>{achievement.value}</p><span><i style={{ width: `${achievement.progress}%` }} /></span></div>
        </article>
      ))}
    </div>
  )
}

function TeacherDashboardPage({ onNavigate, session }) {
  const [activeTab, setActiveTab] = useState(() => getDashboardInitialTab('teacher'))
  useResponsiveDashboardTabs(setActiveTab, 'teacher')
  const [dashboard, setDashboard] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!session?.token) {
      setStatus('guest')
      return
    }

    let cancelled = false
    setStatus('loading')
    fetchTeacherDashboard(session.token)
      .then((payload) => {
        if (cancelled) return
        setDashboard(payload)
        setStatus('ready')
      })
      .catch((requestError) => {
        if (cancelled) return
        setError(requestError.message)
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [session?.token])

  useEffect(() => {
    if (!session?.token || activeTab !== 'schedule') return undefined
    let cancelled = false
    const refreshCalendar = () => {
      fetchTeacherDashboard(session.token, true)
        .then((payload) => { if (!cancelled) setDashboard(payload) })
        .catch(() => {})
    }
    refreshCalendar()
    const refreshTimer = window.setInterval(refreshCalendar, 60_000)
    return () => {
      cancelled = true
      window.clearInterval(refreshTimer)
    }
  }, [activeTab, session?.token])

  if (status === 'guest') {
    return (
      <PageShell>
        <section className="dashboard-empty">
          <h1>Нужно войти в аккаунт</h1>
          <p>Кабинет преподавателя открывается после авторизации.</p>
          <SmartLink href="/login" onNavigate={onNavigate} className="button button--primary">Войти</SmartLink>
        </section>
      </PageShell>
    )
  }

  if (status === 'loading') {
    return <div className="dashboard-loading">Загружаем кабинет преподавателя...</div>
  }

  if (status === 'error') {
    return <div className="dashboard-loading dashboard-loading--error">{error || 'Не удалось загрузить кабинет преподавателя'}</div>
  }

  const tabs = [
    { id: 'overview', label: 'Главная', icon: 'home' },
    { id: 'courses', label: 'Мои предметы', icon: 'books' },
    { id: 'students', label: 'Ученики', icon: 'users' },
    { id: 'schedule', label: 'Расписание', icon: 'calendar' },
    { id: 'messages', label: 'Чаты', icon: 'chat' },
    { id: 'settings', label: 'Настройки', icon: 'settings' },
  ]

  return (
    <div className="student-dashboard-shell teacher-dashboard-shell">
      <aside className="student-sidebar teacher-sidebar">
        <nav aria-label="Кабинет преподавателя">
          {tabs.map((tab) => (
            <button key={tab.id} className={`${activeTab === tab.id ? 'is-active ' : ''}${['messages', 'schedule', 'settings'].includes(tab.id) ? '' : 'dashboard-tab--desktop-only'}`} type="button" onClick={() => setActiveTab(tab.id)}>
              <Icon name={tab.icon} />{tab.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="student-main teacher-main">
        <DashboardTop dashboard={dashboard} />
        {activeTab === 'overview' && <TeacherDashboardOverview dashboard={dashboard} onTabChange={setActiveTab} />}
        {activeTab === 'courses' && <DashboardCoursesPage courses={dashboard.courses} />}
        {activeTab === 'students' && <TeacherStudentsPage token={session.token} students={dashboard.students || []} onUpdated={() => fetchTeacherDashboard(session.token).then(setDashboard)} />}
        {activeTab === 'schedule' && <DashboardSchedulePage lessons={dashboard.lessons} calendarSync={dashboard.settings?.calendar_sync} />}
        {activeTab === 'messages' && <MessagesPage token={session.token} title="Чаты" />}
        {activeTab === 'settings' && <TeacherSettingsPage token={session.token} settings={dashboard.settings} teacher={dashboard.teacher} />}
      </section>
    </div>
  )
}

function TeacherDashboardOverview({ dashboard, onTabChange }) {
  return (
    <>
      <DashboardStats stats={dashboard.stats} />
      <div className="dashboard-grid dashboard-grid--even teacher-dashboard-grid">
        <section className="dashboard-panel dashboard-panel--wide">
          <div className="dashboard-panel__header"><h2>Предметы</h2><button type="button" onClick={() => onTabChange('courses')}>Все предметы</button></div>
          <DashboardCourseList courses={dashboard.courses} />
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-panel__header"><h2>Ближайшие занятия</h2><button type="button" onClick={() => onTabChange('schedule')}>Расписание</button></div>
          <DashboardLessonList lessons={dashboard.lessons.slice(0, 4)} />
        </section>

      </div>
    </>
  )
}

function TeacherStudentsPage({ token, students, onUpdated }) {
  const [drafts, setDrafts] = useState({})
  const [savingId, setSavingId] = useState(null)
  const [status, setStatus] = useState('')

  const updateDraft = (assignmentId, value) => {
    setDrafts((current) => ({ ...current, [assignmentId]: value }))
  }

  const saveDisplayName = async (student) => {
    const value = drafts[student.assignment_id] ?? student.display_name ?? ''
    setSavingId(student.assignment_id)
    setStatus('')
    try {
      await updateTeacherStudentDisplayName(token, student.assignment_id, value)
      setStatus('Имя сохранено')
      onUpdated?.()
    } catch (requestError) {
      setStatus(requestError.message)
    } finally {
      setSavingId(null)
    }
  }

  return (
    <section className="dashboard-panel dashboard-panel--full teacher-students-panel">
      <div className="dashboard-panel__header"><h2>Ученики</h2><span className="dashboard-panel__hint">Имя отображения видно только вам</span></div>
      {status && <p className={status === 'Имя сохранено' ? 'form-success' : 'form-error'}>{status}</p>}
      {students.length === 0 ? (
        <p className="dashboard-list-empty">Пока нет назначенных учеников</p>
      ) : (
        <div className="teacher-student-list teacher-student-list--editable">
          {students.map((student) => (
            <article key={student.assignment_id}>
              <Icon name="profile" />
              <div className="teacher-student-list__info"><b>{student.student_name}</b><span>{student.subject_title}</span></div>
              <label className="teacher-student-display-name"><span>Имя для меня</span><input value={drafts[student.assignment_id] ?? student.display_name ?? ''} placeholder={student.original_name || student.student_name} onChange={(event) => updateDraft(student.assignment_id, event.target.value)} /></label>
              <button className="button button--secondary" type="button" disabled={savingId === student.assignment_id} onClick={() => saveDisplayName(student)}>{savingId === student.assignment_id ? 'Сохраняем…' : 'Сохранить'}</button>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function TeacherSettingsPage({ token, settings, teacher }) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordStatus, setPasswordStatus] = useState('')
  const [saving, setSaving] = useState(false)

  const handlePasswordSubmit = async (event) => {
    event.preventDefault()
    if (newPassword.length < 6 || newPassword !== confirmPassword) {
      setPasswordStatus('Новый пароль должен содержать минимум 6 символов и совпадать с подтверждением')
      return
    }
    setSaving(true)
    setPasswordStatus('')
    try {
      await changePassword(token, currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordStatus('Пароль успешно изменён')
    } catch (requestError) {
      setPasswordStatus(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="dashboard-panel dashboard-panel--full dashboard-settings teacher-settings">
      <div className="dashboard-panel__header"><h2>Настройки</h2></div>
      <div className="settings-profile-grid">
        <label className="settings-field settings-field--readonly">
          <Icon name="profile" />
          <span>Имя</span>
          <input value={settings.profile?.name ?? ''} readOnly />
        </label>
        <label className="settings-field settings-field--readonly">
          <Icon name="document" />
          <span>Почта</span>
          <input value={settings.profile?.email ?? ''} readOnly />
        </label>
        <label className="settings-field settings-field--readonly">
          <Icon name="book" />
          <span>Предмет</span>
          <input value={teacher?.subject_title ?? 'Предмет не назначен'} readOnly />
        </label>
      </div>
      <form className="password-change-form" onSubmit={handlePasswordSubmit}>
        <h3>Смена пароля</h3>
        <label><span>Текущий пароль</span><input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
        <label><span>Новый пароль</span><input type="password" minLength={6} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
        <label><span>Подтвердите новый пароль</span><input type="password" minLength={6} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></label>
        {passwordStatus && <p className={passwordStatus === 'Пароль успешно изменён' ? 'form-success' : 'form-error'}>{passwordStatus}</p>}
        <button className="button button--primary" type="submit" disabled={saving}>{saving ? 'Сохраняем…' : 'Изменить пароль'}</button>
      </form>
    </section>
  )
}

function MessagesPage({ token, title = 'Чаты', canDeleteMessages = false }) {
  const [chats, setChats] = useState([])
  const [selectedChatId, setSelectedChatId] = useState(null)
  const [isMobile, setIsMobile] = useState(isMobileViewport)
  const [detail, setDetail] = useState(null)
  const [message, setMessage] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [integrationStatus, setIntegrationStatus] = useState(null)
  const [sending, setSending] = useState(false)
  const [selectedMessageId, setSelectedMessageId] = useState(null)
  const [deletingMessageId, setDeletingMessageId] = useState(null)
  const messagesEndRef = useRef(null)
  const attachmentInputRef = useRef(null)
  const detailRequestInFlightRef = useRef(false)

  useEffect(() => {
    const media = window.matchMedia?.('(max-width: 760px)')
    if (!media) return undefined
    const updateViewport = () => setIsMobile(media.matches)
    updateViewport()
    media.addEventListener?.('change', updateViewport)
    return () => media.removeEventListener?.('change', updateViewport)
  }, [])

  useEffect(() => {
    let cancelled = false
    const loadChats = (silent = false) => {
      if (!silent) setStatus('loading')
      fetchChats(token)
        .then((payload) => {
          if (cancelled) return
          setChats(payload)
          if (!silent) setError('')
          setSelectedChatId((current) => {
            if (current && payload.some((chat) => chat.id === current)) return current
            return isMobile ? null : payload[0]?.id ?? null
          })
          setStatus('ready')
        })
        .catch((requestError) => {
          if (cancelled) return
          // Background refreshes must not replace a useful transcript or
          // overwrite an error from an explicit send attempt.
          if (!silent) {
            setError(requestError.message)
            setStatus('error')
          }
        })
    }

    loadChats()
    const timerId = window.setInterval(() => loadChats(true), 3000)
    return () => {
      cancelled = true
      window.clearInterval(timerId)
    }
  }, [token, isMobile])

  useEffect(() => {
    fetchTelegramStatus(token).then(setIntegrationStatus).catch(() => setIntegrationStatus(null))
  }, [token])

  useEffect(() => {
    if (!selectedChatId) {
      setDetail(null)
      return
    }
    let cancelled = false
    const loadChat = async () => {
      // Avoid stacking full transcript requests if a slow network or server
      // response takes longer than the polling period.
      if (detailRequestInFlightRef.current) return
      detailRequestInFlightRef.current = true
      try {
        const payload = await fetchChat(token, selectedChatId)
        if (cancelled) return
        setDetail(payload)
        setChats((current) => current.map((chat) => (
          chat.id === selectedChatId ? { ...chat, unread_count: 0 } : chat
        )))
      } catch (requestError) {
        if (!cancelled) setError(requestError.message)
      } finally {
        detailRequestInFlightRef.current = false
      }
    }

    loadChat()
    const timerId = window.setInterval(loadChat, 3000)
    return () => {
      cancelled = true
      window.clearInterval(timerId)
    }
  }, [token, selectedChatId])

  // Also cover programmatic selection changes from the polling refresh. A
  // draft must always belong to exactly one chat.
  useEffect(() => {
    setMessage('')
    setAttachment(null)
    if (attachmentInputRef.current) attachmentInputRef.current.value = ''
    setDetail(null)
    setError('')
    setSelectedMessageId(null)
  }, [selectedChatId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' })
  }, [detail?.messages?.length, selectedChatId])

  const handleSelectChat = (chatId) => {
    if (chatId === selectedChatId) return
    // A draft belongs to the conversation it was written for. Clear it
    // before loading another chat so it cannot be sent to the wrong user.
    setSelectedChatId(chatId)
    setMessage('')
    setAttachment(null)
    if (attachmentInputRef.current) attachmentInputRef.current.value = ''
    setDetail(null)
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const body = message.trim()
    if (!selectedChatId || (!body && !attachment) || sending) return
    setSending(true)
    setError('')
    try {
      const payload = attachment
        ? (['image/jpeg', 'image/png', 'image/webp'].includes(attachment.type)
          ? await sendChatPhoto(token, selectedChatId, attachment, body)
          : await sendChatDocument(token, selectedChatId, attachment, body))
        : await sendChatMessage(token, selectedChatId, body)
      setDetail(payload)
      setMessage('')
      setAttachment(null)
      if (attachmentInputRef.current) attachmentInputRef.current.value = ''
      // Refreshing the sidebar is best-effort. The message has already been
      // accepted by the API, so a transient refresh failure must not make the
      // user think they should send it again.
      try {
        const refreshed = await fetchChats(token)
        setChats(refreshed)
      } catch {
        // The next three-second poll will refresh the sidebar.
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  const handleSelectAttachment = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    const isPhoto = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
    if (file.size > (isPhoto ? 10 : 20) * 1024 * 1024) {
      setError(isPhoto ? 'Фото должно быть не больше 10 МБ' : 'Файл должен быть не больше 20 МБ')
      event.target.value = ''
      return
    }
    setAttachment(file)
    setError('')
  }

  const handleDeleteMessage = async (messageId) => {
    if (!selectedChatId || !canDeleteMessages || deletingMessageId) return
    setDeletingMessageId(messageId)
    setError('')
    try {
      const payload = await deleteChatMessage(token, selectedChatId, messageId)
      setDetail(payload)
      setSelectedMessageId(null)
      const refreshed = await fetchChats(token)
      setChats(refreshed)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDeletingMessageId(null)
    }
  }

  if (status === 'loading') return <section className="dashboard-panel dashboard-panel--full"><p className="dashboard-list-empty">Загружаем сообщения...</p></section>
  if (status === 'error') return <section className="dashboard-panel dashboard-panel--full"><p className="dashboard-list-empty">{error}</p></section>

  return (
    <section className={`dashboard-panel dashboard-panel--full messages-panel ${selectedChatId ? 'is-chat-open' : 'is-chat-list'}`}>
      <div className="dashboard-panel__header">
        {isMobile && selectedChatId && <button className="chat-back" type="button" aria-label="Назад к чатам" onClick={() => { setSelectedChatId(null); setDetail(null); setMessage('') }}>←</button>}
        <h2>{title}</h2>
      </div>
      {integrationStatus && !integrationStatus.configured && <p className="dashboard-list-empty">Telegram не подключён. Укажите TELEGRAM_BOT_TOKEN и перезапустите backend.</p>}
      <div className="messenger-layout">
        <aside className="chat-list">
          {chats.length === 0 && <p className="dashboard-list-empty">Пока нет чатов</p>}
          {chats.map((chat) => (
            <button key={chat.id} className={selectedChatId === chat.id ? 'is-active' : ''} type="button" onClick={() => handleSelectChat(chat.id)}>
              <div className="chat-list__title">
                <strong>{chat.title}</strong>
                {chat.unread_count > 0 && <span className="chat-unread-badge" aria-label={`Непрочитанных сообщений: ${chat.unread_count}`}>{chat.unread_count > 99 ? '99+' : chat.unread_count}</span>}
              </div>
              <span>{chat.last_message || 'Нет сообщений'}</span>
            </button>
          ))}
        </aside>
        <div className="chat-window">
          {detail ? (
            <>
              <div className="chat-window__messages">
                {detail.messages.map((item) => (
                  <article
                    key={item.id}
                    className={`${item.direction === 'outbound' ? 'is-mine ' : ''}${item.reactions?.length ? 'has-reactions ' : ''}${canDeleteMessages && selectedMessageId === item.id ? 'is-selected' : ''}`}
                    onClick={canDeleteMessages ? () => setSelectedMessageId((current) => current === item.id ? null : item.id) : undefined}
                  >
                    <header><b>{item.sender_name}</b><time>{formatMessageTime(item.created_at)}</time></header>
                    {item.has_photo && <ChatPhoto token={token} chatId={selectedChatId} messageId={item.id} />}
                    {item.has_document && <ChatDocument token={token} chatId={selectedChatId} messageId={item.id} name={item.document_name} />}
                    {((!item.has_photo && !item.has_document) || (item.body && !['[Фото]', '[photo]', '[Файл]', '[document]'].includes(item.body))) && <p>{item.body}</p>}
                    {item.reactions?.length > 0 && <div className="chat-reactions" aria-label="Реакции на сообщение">{item.reactions.map((reaction) => <span key={reaction.emoji} title={`${reaction.emoji} · ${reaction.count}`}>{reaction.emoji}{reaction.count > 1 && <small>{reaction.count}</small>}</span>)}</div>}
                    {canDeleteMessages && selectedMessageId === item.id && (
                      <button className="chat-message-delete" type="button" disabled={deletingMessageId === item.id} onClick={(event) => { event.stopPropagation(); handleDeleteMessage(item.id) }}>
                        {deletingMessageId === item.id ? 'Удаляем...' : 'Удалить сообщение'}
                      </button>
                    )}
                  </article>
                ))}
                <span ref={messagesEndRef} />
              </div>
              {error && <p className="form-error">{error}</p>}
              <form className="chat-form" onSubmit={handleSubmit}>
                <label className="chat-attach" title="Прикрепить фото или файл" aria-label="Прикрепить фото или файл">
                  <span aria-hidden="true">＋</span>
                  <input ref={attachmentInputRef} type="file" onChange={handleSelectAttachment} />
                </label>
                <div className="chat-compose">
                  {attachment && <div className="chat-compose__photo"><span title={attachment.name}>📎 {attachment.name}</span><button type="button" onClick={() => { setAttachment(null); if (attachmentInputRef.current) attachmentInputRef.current.value = '' }} aria-label="Убрать вложение">×</button></div>}
                  <input value={message} maxLength={attachment ? 1024 : undefined} onChange={(event) => setMessage(event.target.value)} placeholder={attachment ? 'Подпись к вложению (необязательно)' : 'Сообщение'} />
                </div>
                <button className="button button--primary chat-send-button" type="submit" disabled={sending} aria-label={sending ? 'Отправляем сообщение' : 'Отправить сообщение'} title="Отправить сообщение"><Send aria-hidden="true" /></button>
              </form>
            </>
          ) : <p className="dashboard-list-empty">Выберите чат</p>}
        </div>
      </div>
    </section>
  )
}

function ChatPhoto({ token, chatId, messageId }) {
  const [imageUrl, setImageUrl] = useState('')
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!expanded) return undefined
    const closeOnEscape = (event) => { if (event.key === 'Escape') setExpanded(false) }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [expanded])

  useEffect(() => {
    let cancelled = false
    let objectUrl = ''
    fetchChatPhoto(token, chatId, messageId)
      .then((url) => {
        objectUrl = url
        if (cancelled) URL.revokeObjectURL(url)
        else setImageUrl(url)
      })
      .catch((requestError) => { if (!cancelled) setError(requestError.message) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [token, chatId, messageId])

  if (error) return <span className="chat-photo-error">{error}</span>
  if (!imageUrl) return <span className="chat-photo-loading">Загружаем фото…</span>
  return <>
    <button className="chat-photo-link" type="button" onClick={(event) => { event.stopPropagation(); setExpanded(true) }} aria-label="Открыть фото в чате"><img src={imageUrl} alt="Фотография из чата" loading="lazy" /></button>
    {expanded && <div className="chat-photo-viewer" role="dialog" aria-modal="true" aria-label="Просмотр фотографии" onClick={(event) => { event.stopPropagation(); setExpanded(false) }}>
      <button type="button" className="chat-photo-viewer__close" aria-label="Закрыть фото" onClick={() => setExpanded(false)}>×</button>
      <img src={imageUrl} alt="Фотография из чата" onClick={(event) => event.stopPropagation()} />
    </div>}
  </>
}

function ChatDocument({ token, chatId, messageId, name }) {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const filename = name || 'Файл'

  const handleDownload = async (event) => {
    event.stopPropagation()
    if (loading) return
    setLoading(true)
    setError('')
    try {
      const blob = await fetchChatDocument(token, chatId, messageId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return <div><button className="chat-document" type="button" disabled={loading} onClick={handleDownload}><span aria-hidden="true">📄</span><span>{filename}</span><span>{loading ? 'Загрузка…' : 'Скачать ↓'}</span></button>{error && <span className="chat-photo-error">{error}</span>}</div>
}

function formatMessageTime(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function AdminDashboardPage({ onNavigate, session, data }) {
  const [activeTab, setActiveTab] = useState(() => getDashboardInitialTab('admin'))
  useResponsiveDashboardTabs(setActiveTab, 'admin')
  const [dashboard, setDashboard] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!session?.token) {
      setStatus('guest')
      return
    }
    let cancelled = false
    setStatus('loading')
    fetchAdminDashboard(session.token)
      .then((payload) => {
        if (cancelled) return
        setDashboard(payload)
        setStatus('ready')
      })
      .catch((requestError) => {
        if (cancelled) return
        setError(requestError.message)
        setStatus('error')
      })
    return () => { cancelled = true }
  }, [session?.token])

  useEffect(() => {
    if (!session?.token) return undefined
    let cancelled = false
    const refreshTimer = window.setInterval(() => {
      fetchAdminDashboard(session.token)
        .then((payload) => { if (!cancelled) setDashboard(payload) })
        .catch(() => {})
    }, 10_000)
    return () => {
      cancelled = true
      window.clearInterval(refreshTimer)
    }
  }, [session?.token])

  if (status === 'guest') {
    return <PageShell><section className="dashboard-empty"><h1>Нужно войти</h1><SmartLink href="/login" onNavigate={onNavigate} className="button button--primary">Войти</SmartLink></section></PageShell>
  }
  if (status === 'loading') return <div className="dashboard-loading">Загружаем панель администратора...</div>
  if (status === 'error') return <div className="dashboard-loading dashboard-loading--error">{error}</div>

  const newRequestsCount = Number(dashboard.stats.find((item) => item.id === 'requests')?.value || 0)
  const tabs = [
    { id: 'overview', label: 'Аналитика', icon: 'chart' },
    { id: 'requests', label: 'Заявки', icon: 'document', badge: newRequestsCount },
    { id: 'students', label: 'Ученики', icon: 'users' },
    { id: 'teachers', label: 'Учителя', icon: 'graduation' },
    { id: 'messages', label: 'Чаты', icon: 'chat' },
  ]

  return (
    <div className="student-dashboard-shell admin-dashboard-shell">
      <aside className="student-sidebar admin-sidebar">
        <nav aria-label="Кабинет администратора">
          {tabs.map((tab) => (
            <button key={tab.id} className={`${activeTab === tab.id ? 'is-active ' : ''}${['messages', 'schedule', 'settings'].includes(tab.id) ? '' : 'dashboard-tab--desktop-only'}`} type="button" onClick={() => setActiveTab(tab.id)}>
              <Icon name={tab.icon} />{tab.label}{tab.badge > 0 && <span className="dashboard-tab-badge" aria-label={`Новых заявок: ${tab.badge}`}>{tab.badge > 99 ? '99+' : tab.badge}</span>}
            </button>
          ))}
        </nav>
      </aside>
      <nav className="mobile-dashboard-tabs admin-mobile-dashboard-tabs" aria-label="Мобильная навигация">
        <button className={activeTab === 'messages' ? 'is-active' : ''} type="button" onClick={() => setActiveTab('messages')}><Icon name="chat" />Чаты</button>
        <button className={activeTab === 'teachers' ? 'is-active' : ''} type="button" onClick={() => setActiveTab('teachers')}><Icon name="profile" />Учителя</button>
      </nav>
      <section className="student-main admin-main">
        <DashboardTop dashboard={dashboard} />
        {activeTab === 'overview' && <DashboardStats stats={dashboard.stats} />}
        {activeTab === 'requests' && <AdminRequestsPage token={session.token} teachers={data.teachers} onRequestsChanged={() => fetchAdminDashboard(session.token).then(setDashboard).catch(() => {})} />}
        {activeTab === 'students' && <AdminUsersPage token={session.token} role="student" title="Ученики" />}
        {activeTab === 'teachers' && <AdminUsersPage token={session.token} role="teacher" title="Учителя" subjects={data.subjects} />}
        {activeTab === 'messages' && <MessagesPage token={session.token} title="Чаты" canDeleteMessages />}
        {activeTab === 'schedule' && <DashboardSchedulePage lessons={dashboard.lessons || []} />}
        {activeTab === 'settings' && <AdminSettingsPage session={session} />}
      </section>
    </div>
  )
}

function AdminSettingsPage({ session }) {
  return (
    <section className="dashboard-panel dashboard-panel--full dashboard-settings admin-settings">
      <div className="dashboard-panel__header"><h2>Настройки</h2></div>
      <div className="settings-profile-grid">
        <label className="settings-field settings-field--readonly"><Icon name="profile" /><span>Имя</span><input value={session?.user?.full_name ?? ''} readOnly /></label>
        <label className="settings-field settings-field--readonly"><Icon name="document" /><span>Почта</span><input value={session?.user?.email ?? ''} readOnly /></label>
      </div>
    </section>
  )
}

function AdminUsersPage({ token, role, title, subjects = [] }) {
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [teacherStudents, setTeacherStudents] = useState(null)
  const [showCreateStudent, setShowCreateStudent] = useState(false)
  const [showCreateTeacher, setShowCreateTeacher] = useState(false)
  const [showCreateSubject, setShowCreateSubject] = useState(false)
  const [availableSubjects, setAvailableSubjects] = useState(subjects)
  const [movingTeacherId, setMovingTeacherId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => setAvailableSubjects(subjects), [subjects])

  const loadUsers = () => fetchAdminUsers(token, role, query).then(setUsers).catch((requestError) => setError(requestError.message))

  useEffect(() => {
    let cancelled = false
    fetchAdminUsers(token, role, query)
      .then((payload) => { if (!cancelled) setUsers(payload) })
      .catch((requestError) => { if (!cancelled) setError(requestError.message) })
    return () => { cancelled = true }
  }, [token, role, query])

  const openUser = async (userId) => {
    const payload = await fetchAdminUser(token, userId)
    setSelectedUser(payload)
  }

  const removeUser = async (user) => {
    if (!window.confirm(`Удалить ${user.full_name} из системы?`)) return
    try {
      await deleteAdminUser(token, user.id)
      setSelectedUser(null)
      setError('')
      await loadUsers()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const moveTeacher = async (user, action) => {
    setMovingTeacherId(user.id)
    setError('')
    try {
      await reorderAdminTeacher(token, user.id, action)
      await loadUsers()
      window.dispatchEvent(new Event('idioma:teachers-updated'))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setMovingTeacherId(null)
    }
  }

  return (
    <section className="dashboard-panel dashboard-panel--full admin-users-panel">
      <div className="dashboard-panel__header"><h2>{title}</h2>{role === 'student' && <button className="button button--primary" type="button" onClick={() => setShowCreateStudent(true)}>Добавить ученика</button>}{role === 'teacher' && <div className="admin-header-actions"><button className="button button--secondary" type="button" onClick={() => setShowCreateSubject(true)}>Управление предметами</button><button className="button button--primary" type="button" onClick={() => setShowCreateTeacher(true)}>Добавить учителя</button></div>}</div>
      <label className="search-field admin-user-search"><Icon name="search" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по имени, Telegram ID или username" /></label>
      {error && <p className="dashboard-list-empty">{error}</p>}
      <div className="admin-user-list">
        {users.map((user) => (
          <div className="admin-user-row" key={user.id}>
            <button type="button" onClick={() => openUser(user.id)}>
              <Icon name={user.role === 'teacher' ? 'graduation' : 'profile'} />
              <span><b>{user.full_name}</b><small>{user.role === 'student' && user.telegram_user_id ? `Telegram ID: ${user.telegram_user_id}${user.telegram_username ? ` · @${user.telegram_username}` : ''}` : user.email}{user.teacher_profile ? ` · ${user.teacher_profile.subject_title} · позиция ${user.teacher_profile.sort_order}` : ''}</small></span>
              <mark>{user.role}</mark>
            </button>
            <div className="admin-user-actions">
              {role === 'teacher' ? (
                <>
                  <div className="admin-teacher-order" aria-label={`Порядок преподавателя ${user.full_name}`}>
                    <button className="admin-order-button" type="button" title="Переместить в начало" aria-label="Переместить в начало" disabled={movingTeacherId === user.id} onClick={() => moveTeacher(user, 'first')}>⇈</button>
                    <button className="admin-order-button" type="button" title="Переместить выше" aria-label="Переместить выше" disabled={movingTeacherId === user.id} onClick={() => moveTeacher(user, 'up')}>↑</button>
                    <button className="admin-order-button" type="button" title="Переместить ниже" aria-label="Переместить ниже" disabled={movingTeacherId === user.id} onClick={() => moveTeacher(user, 'down')}>↓</button>
                  </div>
                  <button className="button button--secondary admin-assign-button" type="button" onClick={() => setTeacherStudents(user)}>Ученики</button>
                </>
              ) : (
                <button className="button button--danger admin-delete-button" type="button" onClick={() => removeUser(user)}>Удалить</button>
              )}
            </div>
          </div>
        ))}
      </div>
      {selectedUser && <UserDetailModal token={token} subjects={availableSubjects} user={selectedUser} onClose={() => setSelectedUser(null)} onDelete={() => removeUser(selectedUser)} onUpdated={() => openUser(selectedUser.id)} />}
      {showCreateStudent && <CreateStudentModal token={token} onClose={() => setShowCreateStudent(false)} onCreated={() => { setShowCreateStudent(false); loadUsers() }} />}
      {showCreateTeacher && <CreateTeacherModal token={token} subjects={availableSubjects} onClose={() => setShowCreateTeacher(false)} onCreated={() => { setShowCreateTeacher(false); loadUsers() }} />}
      {showCreateSubject && <CreateSubjectModal token={token} subjects={availableSubjects} onClose={() => setShowCreateSubject(false)} onCreated={(subject) => setAvailableSubjects((current) => [...current.filter((item) => item.id !== subject.id), subject])} onDeleted={(subjectId) => setAvailableSubjects((current) => current.filter((subject) => subject.id !== subjectId))} />}
      {teacherStudents && <AssignStudentModal token={token} teacher={teacherStudents} onClose={() => setTeacherStudents(null)} />}
    </section>
  )
}

function CreateStudentModal({ token, onClose, onCreated }) {
  const [form, setForm] = useState({ fullName: '', telegramUserId: '', telegramUsername: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    if (!form.fullName.trim() || !form.telegramUserId) return
    setSaving(true)
    try {
      await createAdminStudent(token, { full_name: form.fullName.trim(), telegram_user_id: Number(form.telegramUserId), telegram_username: form.telegramUsername.trim() || null })
      onCreated()
    } catch (requestError) {
      setError(requestError.message)
      setSaving(false)
    }
  }
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><article className="user-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><button className="user-modal__close" type="button" onClick={onClose}>×</button><h2>Добавить ученика</h2><form className="admin-modal-form" onSubmit={submit}><label>Имя<input value={form.fullName} onChange={update('fullName')} required /></label><label>Telegram ID<input type="number" min="1" value={form.telegramUserId} onChange={update('telegramUserId')} required /></label><label>Username<input value={form.telegramUsername} onChange={update('telegramUsername')} placeholder="username без @" /></label>{error && <p className="form-error">{error}</p>}<button className="button button--primary" type="submit" disabled={saving}>{saving ? 'Сохраняем…' : 'Добавить'}</button></form></article></div>
}

function SubjectMultiPicker({ subjects = [], value = [], onChange }) {
  const selected = new Set(value)
  const toggle = (slug) => {
    const next = new Set(selected)
    if (next.has(slug)) next.delete(slug)
    else next.add(slug)
    onChange([...next])
  }
  return (
    <div className="admin-subject-picker" role="group" aria-label="Предметы преподавателя">
      {subjects.map((subject) => (
        <label key={subject.slug} className={selected.has(subject.slug) ? 'is-selected' : ''}>
          <input type="checkbox" checked={selected.has(subject.slug)} onChange={() => toggle(subject.slug)} />
          <span><Icon name={subject.icon || 'book'} size={20} /><b>{subject.title}</b><small>{subject.category}</small></span>
        </label>
      ))}
      {subjects.length === 0 && <p className="dashboard-list-empty">Сначала добавьте хотя бы один предмет.</p>}
    </div>
  )
}

function CreateTeacherModal({ token, subjects, onClose, onCreated }) {
  const availableSubjects = subjects ?? []
  const firstSubject = availableSubjects[0]?.slug ?? ''
  const [form, setForm] = useState({ fullName: '', email: '', password: '', role: 'Преподаватель', description: '', subjectSlugs: firstSubject ? [firstSubject] : [], initials: '', rating: '4.9', lessonPrice: '1500', avatarUrl: '', calendarUrl: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    if (!form.fullName.trim() || !form.email.trim() || !form.password || !form.description.trim()) return
    if (form.subjectSlugs.length === 0) {
      setError('Выберите хотя бы один предмет')
      return
    }
    setSaving(true)
    try {
      await createAdminTeacher(token, {
        full_name: form.fullName.trim(), email: form.email.trim(), password: form.password,
        role: form.role.trim(), description: form.description.trim(), subject_slugs: form.subjectSlugs, subject_slug: form.subjectSlugs[0],
        initials: form.initials.trim() || null, rating: Number(form.rating || 4.9), lesson_price: Number(form.lessonPrice || 0), avatar_url: form.avatarUrl || null,
        calendar_url: form.calendarUrl.trim() || null,
      })
      onCreated()
    } catch (requestError) {
      setError(requestError.message)
      setSaving(false)
    }
  }
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><article className="user-modal user-modal--wide" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><button className="user-modal__close" type="button" onClick={onClose}>×</button><h2>Добавить учителя</h2><form className="admin-modal-form admin-teacher-form" onSubmit={submit}><label>Имя и фамилия<input value={form.fullName} onChange={update('fullName')} required /></label><label>Email<input type="email" value={form.email} onChange={update('email')} required /></label><label>Пароль<input type="password" minLength={6} value={form.password} onChange={update('password')} required /></label><label>Должность<input value={form.role} onChange={update('role')} required /></label><label>Описание<textarea value={form.description} onChange={update('description')} required /></label><div className="admin-modal-form__field"><span className="admin-modal-form__field-heading">Предметы и категории <b>Выбрано: {form.subjectSlugs.length}</b></span><SubjectMultiPicker subjects={availableSubjects} value={form.subjectSlugs} onChange={(subjectSlugs) => setForm((current) => ({ ...current, subjectSlugs }))} /><small>Можно выбрать несколько предметов — нажмите на нужные карточки.</small></div><div className="admin-teacher-form__row"><label>Инициалы<input value={form.initials} onChange={update('initials')} placeholder="АИ" /></label><label>Рейтинг<input type="number" min="0" max="9.9" step="0.1" value={form.rating} onChange={update('rating')} /></label><label>Цена урока, ₽/час<input type="number" min="0" value={form.lessonPrice} onChange={update('lessonPrice')} /></label></div><label>Ссылка Google Calendar (iCal)<input type="url" value={form.calendarUrl} onChange={update('calendarUrl')} placeholder="https://calendar.google.com/calendar/ical/.../basic.ics" /><small>Вставьте секретный адрес в формате iCal из настроек календаря. Ссылка доступна только администратору.</small></label><label>Аватар<input type="file" accept="image/*" onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; if (file.size > 1_500_000) { setError('Изображение должно быть меньше 1,5 МБ'); return } const reader = new FileReader(); reader.onload = () => setForm((current) => ({ ...current, avatarUrl: String(reader.result) })); reader.readAsDataURL(file) }} /></label>{error && <p className="form-error">{error}</p>}<button className="button button--primary" type="submit" disabled={saving}>{saving ? 'Сохраняем…' : 'Создать учителя'}</button></form></article></div>
}

function CreateSubjectModal({ token, subjects = [], onClose, onCreated, onDeleted }) {
  const [form, setForm] = useState({ slug: '', title: '', category: 'school', examType: '', description: '', priceMonth: '700', icon: 'book', tint: 'peach' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const categories = [...new Set([...Object.keys(categoryLabels), ...subjects.map((subject) => subject.category).filter(Boolean)])]
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const subject = await createAdminSubject(token, { slug: form.slug, title: form.title, category: form.category, exam_type: form.examType || null, description: form.description, price_month: Number(form.priceMonth || 0), icon: form.icon, tint: form.tint })
      onCreated(subject)
      setForm({ slug: '', title: '', category: form.category, examType: '', description: '', priceMonth: '700', icon: 'book', tint: 'peach' })
      setSuccess(`Предмет «${subject.title}» добавлен`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }
  const removeSubject = async (subject) => {
    if (!window.confirm(`Удалить предмет «${subject.title}»?`)) return
    setDeletingId(subject.id)
    setError('')
    setSuccess('')
    try {
      await deleteAdminSubject(token, subject.id)
      onDeleted(subject.id)
      setSuccess(`Предмет «${subject.title}» удалён`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDeletingId(null)
    }
  }
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <article className="user-modal user-modal--wide subject-manager-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button className="user-modal__close" type="button" onClick={onClose}>×</button>
        <h2>Управление предметами</h2>
        <section className="subject-manager-list">
          <h3>Предметы в системе ({subjects.length})</h3>
          <div>{subjects.map((subject) => <article key={subject.id}><Icon name={subject.icon || 'book'} size={24} /><span><b>{subject.title}</b><small>{categoryLabels[subject.category] ?? subject.category}</small></span><button className="button button--danger" type="button" disabled={deletingId === subject.id} onClick={() => removeSubject(subject)}>{deletingId === subject.id ? 'Удаляем…' : 'Удалить'}</button></article>)}</div>
        </section>
        <form className="admin-modal-form" onSubmit={submit}>
          <h3>Добавить новый предмет</h3>
          <label>Название<input value={form.title} onChange={update('title')} required /></label>
          <label>Slug<input value={form.slug} onChange={update('slug')} placeholder="например, algebra" required /></label>
          <div className="admin-teacher-form__row">
            <label>Выбрать категорию<select value={categories.includes(form.category) ? form.category : ''} onChange={(event) => event.target.value && setForm((current) => ({ ...current, category: event.target.value }))}><option value="">Своя категория</option>{categories.map((category) => <option key={category} value={category}>{categoryLabels[category] ?? category}</option>)}</select></label>
            <label>Или ввести категорию<input value={form.category} onChange={update('category')} placeholder="например, music" required /></label>
          </div>
          <label>Тип экзамена<input value={form.examType} onChange={update('examType')} placeholder="ЕГЭ / ОГЭ (если нужен)" /></label>
          <label>Описание<textarea value={form.description} onChange={update('description')} required /></label>
          <div className="admin-teacher-form__row"><label>Стоимость, ₽/мес<input type="number" min="0" value={form.priceMonth} onChange={update('priceMonth')} /></label><label>Иконка<select value={form.icon} onChange={update('icon')} required>{subjectIconOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Цвет карточки<input value={form.tint} onChange={update('tint')} placeholder="peach, sky, mint…" /></label></div>
          {error && <p className="form-error">{error}</p>}{success && <p className="form-success">{success}</p>}
          <button className="button button--primary" type="submit" disabled={saving}>{saving ? 'Сохраняем…' : 'Добавить предмет'}</button>
        </form>
      </article>
    </div>
  )
}

function AssignStudentModal({ token, teacher, onClose }) {
  const [students, setStudents] = useState([])
  const [assigned, setAssigned] = useState([])
  const [studentId, setStudentId] = useState('')
  const [status, setStatus] = useState('')
  useEffect(() => {
    Promise.all([fetchAdminUsers(token, 'student'), fetchTeacherStudents(token, teacher.id)])
      .then(([allStudents, current]) => {
        setStudents(allStudents)
        setAssigned(current)
        setStudentId(allStudents.find((student) => !current.some((item) => item.student_id === student.id))?.id ?? '')
      })
      .catch((requestError) => setStatus(requestError.message))
  }, [token, teacher.id])
  const submit = async (event) => {
    event.preventDefault()
    if (!studentId) return
    try {
      const item = await assignStudentToTeacher(token, teacher.id, studentId)
      const nextAssigned = assigned.some((entry) => entry.assignment_id === item.assignment_id) ? assigned : [...assigned, item]
      setAssigned(nextAssigned)
      setStudentId(students.find((student) => !nextAssigned.some((entry) => entry.student_id === student.id))?.id ?? '')
      setStatus('Ученик назначен')
    } catch (requestError) { setStatus(requestError.message) }
  }
  const removeAssignment = async (item) => {
    if (!window.confirm(`Убрать ${item.student_name} из назначений?`)) return
    try {
      await removeStudentFromTeacher(token, teacher.id, item.assignment_id)
      setAssigned((current) => current.filter((entry) => entry.assignment_id !== item.assignment_id))
      setStatus('Ученик убран из назначений')
    } catch (requestError) { setStatus(requestError.message) }
  }
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><article className="user-modal user-modal--wide" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><button className="user-modal__close" type="button" onClick={onClose}>×</button><h2>Ученики преподавателя</h2><p>{teacher.full_name}</p><form className="admin-modal-form" onSubmit={submit}><label>Добавить ученика<select value={studentId} onChange={(event) => setStudentId(event.target.value)}><option value="">Выберите ученика</option>{students.filter((student) => !assigned.some((item) => item.student_id === student.id)).map((student) => <option key={student.id} value={student.id}>{student.full_name} · Telegram {student.telegram_user_id ?? 'не указан'}</option>)}</select></label><button className="button button--primary" type="submit">Назначить ученика</button></form>{status && <p className={status === 'Ученик назначен' || status === 'Ученик убран из назначений' ? 'form-success' : 'form-error'}>{status}</p>}<h3>Назначенные ученики ({assigned.length})</h3>{assigned.length === 0 ? <p className="dashboard-list-empty">Пока нет назначенных учеников</p> : <ul className="admin-assigned-list">{assigned.map((item) => <li key={item.assignment_id}><span><b>{item.student_name}</b> · {item.subject_title} · {item.telegram_user_id ? `Telegram ID: ${item.telegram_user_id}` : item.student_email}</span><button className="button button--danger admin-assignment-remove" type="button" onClick={() => removeAssignment(item)}>Убрать</button></li>)}</ul>}</article></div>
}

function AdminRequestsPage({ token, teachers, onRequestsChanged }) {
  const [requests, setRequests] = useState([])
  const [teacherApplications, setTeacherApplications] = useState([])
  const [formById, setFormById] = useState({})
  const [statusById, setStatusById] = useState({})
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState('')

  const loadRequests = () => {
    Promise.all([fetchCourseRequests(token, 'new'), fetchTeacherApplications(token, 'new')])
      .then(([courseRequests, applications]) => {
        setRequests(courseRequests)
        setTeacherApplications(applications)
      })
      .catch((requestError) => setError(requestError.message))
  }

  useEffect(() => {
    loadRequests()
    const refreshTimer = window.setInterval(loadRequests, 10_000)
    return () => window.clearInterval(refreshTimer)
  }, [token])

  const updateForm = (requestId, patch) => {
    setFormById((current) => ({ ...current, [requestId]: { ...(current[requestId] || {}), ...patch } }))
  }

  const updateScheduleSlot = (requestId, index, patch) => {
    setFormById((current) => {
      const form = current[requestId] || {}
      const slots = getScheduleSlots(form).map((slot, slotIndex) => (slotIndex === index ? { ...slot, ...patch } : slot))
      return { ...current, [requestId]: { ...form, slots } }
    })
  }

  const addScheduleSlot = (requestId) => {
    setFormById((current) => {
      const form = current[requestId] || {}
      return { ...current, [requestId]: { ...form, slots: [...getScheduleSlots(form), createScheduleSlot()] } }
    })
  }

  const removeScheduleSlot = (requestId, index) => {
    setFormById((current) => {
      const form = current[requestId] || {}
      const slots = getScheduleSlots(form).filter((_, slotIndex) => slotIndex !== index)
      return { ...current, [requestId]: { ...form, slots: slots.length ? slots : [createScheduleSlot()] } }
    })
  }

  const handleSchedule = async (event, request) => {
    event.preventDefault()
    const form = formById[request.id] || { teacherId: request.teacher_id ? String(request.teacher_id) : '' }
    const slots = getScheduleSlots(form).filter((slot) => slot.time)
    if (!form.teacherId || slots.length === 0 || !form.topic) return
    setStatusById((current) => ({ ...current, [request.id]: 'loading' }))
    try {
      await scheduleCourseRequest(token, request.id, {
        teacher_id: Number(form.teacherId),
        slots: slots.map((slot) => ({ weekday: Number(slot.weekday), time: slot.time })),
        duration_minutes: Number(form.duration || 60),
        weeks_count: Number(form.weeksCount || 12),
        topic: form.topic,
      })
      setStatusById((current) => ({ ...current, [request.id]: 'success' }))
      loadRequests()
      onRequestsChanged?.()
    } catch (requestError) {
      setStatusById((current) => ({ ...current, [request.id]: requestError.message }))
    }
  }

  const handleDelete = async (request) => {
    if (!window.confirm(`Удалить заявку «${request.subject_title}» от ${request.contact_name || request.student_name}?`)) return
    setDeletingId(`course-${request.id}`)
    setError('')
    try {
      await deleteCourseRequest(token, request.id)
      setRequests((current) => current.filter((item) => item.id !== request.id))
      onRequestsChanged?.()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDeletingId(null)
    }
  }

  const handleDeleteTeacherApplication = async (application) => {
    if (!window.confirm(`Удалить заявку преподавателя от ${application.name}?`)) return
    setDeletingId(`teacher-${application.id}`)
    setError('')
    try {
      await deleteTeacherApplication(token, application.id)
      setTeacherApplications((current) => current.filter((item) => item.id !== application.id))
      onRequestsChanged?.()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="dashboard-panel dashboard-panel--full admin-requests-panel">
      <div className="dashboard-panel__header"><h2>Заявки</h2></div>
      {error && <p className="dashboard-list-empty">{error}</p>}
      {requests.length === 0 && teacherApplications.length === 0 ? (
        <p className="dashboard-list-empty">Пока нет заявок</p>
      ) : (
        <div className="admin-request-list">
          {teacherApplications.map((application) => {
            const contactMethod = { telegram: 'Telegram', max: 'MAX', phone: 'Телефон', email: 'Почта' }[application.contact_method] || 'Контакт'
            return (
              <article key={`teacher-${application.id}`} className="admin-teacher-application-card">
                <div className="admin-request-card__info">
                  <Icon name="graduation" />
                  <div>
                    <h3>Хочет преподавать: {application.subjects}</h3>
                    <p>{application.name}</p>
                    <a className="admin-request-contact" href={application.contact_method === 'email' ? `mailto:${application.contact_value}` : application.contact_method === 'phone' ? `tel:${application.contact_value}` : undefined}>{contactMethod}: {application.contact_value}</a>
                    <span>{application.note || 'Без комментария'}</span>
                    <small>{new Date(application.created_at).toLocaleString('ru-RU')}</small>
                  </div>
                  <div className="admin-request-card__actions">
                    <mark>Кандидат</mark>
                    <button className="button button--danger" type="button" disabled={deletingId === `teacher-${application.id}`} onClick={() => handleDeleteTeacherApplication(application)}>{deletingId === `teacher-${application.id}` ? 'Удаляем…' : 'Удалить'}</button>
                  </div>
                </div>
              </article>
            )
          })}
          {requests.map((request) => {
            const form = formById[request.id] || { teacherId: request.teacher_id ? String(request.teacher_id) : '' }
            const status = statusById[request.id]
            const slots = getScheduleSlots(form)
            const contactMethod = { telegram: 'Telegram', max: 'MAX', phone: 'Телефон', email: 'Почта' }[request.contact_method] || 'Контакт'
            return (
              <article key={request.id}>
                <div className="admin-request-card__info">
                  <Icon name="document" />
                  <div>
                    <h3>{request.subject_title}</h3>
                    <p>{request.contact_name || request.student_name}{request.teacher_name ? ` · преподаватель: ${request.teacher_name}` : ''}</p>
                    <a className="admin-request-contact" href={request.contact_method === 'email' ? `mailto:${request.contact_value}` : request.contact_method === 'phone' ? `tel:${request.contact_value}` : undefined}>{contactMethod}: {request.contact_value}</a>
                    <span>{request.note || 'Без комментария'}</span>
                  </div>
                  <div className="admin-request-card__actions">
                    <mark>{request.status}</mark>
                    <button className="button button--danger" type="button" disabled={deletingId === `course-${request.id}`} onClick={() => handleDelete(request)}>{deletingId === `course-${request.id}` ? 'Удаляем…' : 'Удалить'}</button>
                  </div>
                </div>
                {request.student_id ? <form className="admin-schedule-form" onSubmit={(event) => handleSchedule(event, request)}>
                  <select value={form.teacherId || ''} onChange={(event) => updateForm(request.id, { teacherId: event.target.value })}>
                    <option value="">Выберите преподавателя</option>
                    {teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.name} · {teacher.role}</option>)}
                  </select>
                  <div className="schedule-slot-list">
                    {slots.map((slot, index) => (
                      <div className="schedule-slot-row" key={`${request.id}-${index}`}>
                        <select value={slot.weekday} onChange={(event) => updateScheduleSlot(request.id, index, { weekday: event.target.value })}>
                          {weekDayOptions.map((day) => <option key={day.value} value={day.value}>{day.label}</option>)}
                        </select>
                        <input type="time" value={slot.time} onChange={(event) => updateScheduleSlot(request.id, index, { time: event.target.value })} />
                        {slots.length > 1 && <button className="button button--secondary schedule-slot-remove" type="button" onClick={() => removeScheduleSlot(request.id, index)}>Убрать</button>}
                      </div>
                    ))}
                    <button className="button button--secondary schedule-slot-add" type="button" onClick={() => addScheduleSlot(request.id)}>Добавить день</button>
                  </div>
                  <input value={form.topic || ''} onChange={(event) => updateForm(request.id, { topic: event.target.value })} placeholder="Тема урока" />
                  <input type="number" min="20" max="240" value={form.duration || 60} onChange={(event) => updateForm(request.id, { duration: event.target.value })} aria-label="Длительность урока в минутах" title="Длительность, минут" />
                  <input type="number" min="1" max="52" value={form.weeksCount || 12} onChange={(event) => updateForm(request.id, { weeksCount: event.target.value })} aria-label="Количество недель" title="Количество недель" />
                  <button className="button button--primary" type="submit" disabled={status === 'loading'}>Назначить урок</button>
                </form> : <p className="admin-request-guest-note">Заявка отправлена без аккаунта. Свяжитесь с человеком по указанному контакту.</p>}
                {status && status !== 'loading' && status !== 'success' && <p className="form-error">{status}</p>}
                {status === 'success' && <p className="form-success">Урок назначен</p>}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function UserDetailModal({ token, subjects = [], user, onClose, onDelete, onUpdated }) {
  const profile = user.teacher_profile
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState(() => ({ fullName: user.full_name, role: profile?.role ?? '', description: profile?.description ?? '', subjectSlugs: profile?.subjects?.map((subject) => subject.slug) ?? (profile?.subject_slug ? [profile.subject_slug] : []), initials: profile?.initials ?? '', rating: String(profile?.rating ?? 4.9), lessonPrice: String(profile?.lesson_price ?? 1500), avatarUrl: profile?.avatar_url ?? '', calendarUrl: profile?.calendar_url ?? '' }))
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))
  const save = async (event) => {
    event.preventDefault()
    if (form.subjectSlugs.length === 0) {
      setError('Выберите хотя бы один предмет')
      return
    }
    setSaving(true)
    setError('')
    try {
      await updateAdminTeacher(token, user.id, { full_name: form.fullName.trim(), role: form.role.trim(), description: form.description.trim(), subject_slugs: form.subjectSlugs, initials: form.initials.trim() || null, rating: Number(form.rating || 4.9), lesson_price: Number(form.lessonPrice || 0), avatar_url: form.avatarUrl || null, calendar_url: form.calendarUrl.trim() || null })
      setEditing(false)
      onUpdated?.()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <article className="user-modal user-modal--wide" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button className="user-modal__close" type="button" onClick={onClose}>×</button>
        <Icon name={user.role === 'teacher' ? 'graduation' : 'profile'} size={42} />
        {!editing ? <>
          <h2>{user.full_name}</h2><p>{user.email}</p>
          <dl>
            <dt>Роль</dt><dd>{user.role}</dd><dt>Логин</dt><dd>{user.email}</dd>
            {user.role === 'student' && <><dt>Telegram ID</dt><dd>{user.telegram_user_id ?? 'не указан'}</dd><dt>Telegram username</dt><dd>{user.telegram_username ? `@${user.telegram_username}` : 'не указан'}</dd></>}
            {profile && <><dt>Должность</dt><dd>{profile.role}</dd><dt>Предметы</dt><dd>{profile.subjects?.map((subject) => subject.title).join(', ') || profile.subject_title}</dd><dt>Категории</dt><dd>{profile.categories?.join(', ') || '—'}</dd><dt>Цена часа</dt><dd>{profile.lesson_price?.toLocaleString('ru-RU')} ₽</dd><dt>Рейтинг</dt><dd>{Number(profile.rating).toFixed(1)}</dd><dt>Описание</dt><dd>{profile.description}</dd><dt>Google Calendar</dt><dd>{profile.calendar_url ? <a className="admin-calendar-link" href={profile.calendar_url} target="_blank" rel="noreferrer">Открыть iCal-ссылку</a> : 'не указан'}</dd></>}
            <dt>Пароль</dt><dd>{user.password_status}</dd><dt>Безопасность</dt><dd>{user.password_note}</dd>
          </dl>
          {profile && <button className="button button--secondary" type="button" onClick={() => setEditing(true)}>Редактировать профиль</button>}
          {onDelete && <button className="button button--danger" type="button" onClick={onDelete}>Удалить пользователя</button>}
        </> : <form className="admin-modal-form" onSubmit={save}>
          <h2>Профиль преподавателя</h2>
          <label>Имя и фамилия<input value={form.fullName} onChange={update('fullName')} required /></label>
          <label>Должность<input value={form.role} onChange={update('role')} required /></label>
          <label>Описание<textarea value={form.description} onChange={update('description')} required /></label>
          <div className="admin-modal-form__field"><span className="admin-modal-form__field-heading">Предметы и категории <b>Выбрано: {form.subjectSlugs.length}</b></span><SubjectMultiPicker subjects={subjects} value={form.subjectSlugs} onChange={(subjectSlugs) => setForm((current) => ({ ...current, subjectSlugs }))} /><small>Можно выбрать несколько предметов — нажмите на нужные карточки.</small></div>
          <div className="admin-teacher-form__row"><label>Инициалы<input value={form.initials} onChange={update('initials')} /></label><label>Рейтинг<input type="number" min="0" max="9.9" step="0.1" value={form.rating} onChange={update('rating')} /></label><label>Цена урока, ₽/час<input type="number" min="0" value={form.lessonPrice} onChange={update('lessonPrice')} /></label></div>
          <label>Ссылка Google Calendar (iCal)<input type="url" value={form.calendarUrl} onChange={update('calendarUrl')} placeholder="https://calendar.google.com/calendar/ical/.../basic.ics" /><small>Вставьте секретный адрес в формате iCal. В расписание попадут только события с названием, начинающимся на «Урок».</small></label>
          <label>Аватар<input type="file" accept="image/*" onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => setForm((current) => ({ ...current, avatarUrl: String(reader.result) })); reader.readAsDataURL(file) }} /></label>
          {error && <p className="form-error">{error}</p>}<div className="admin-modal-actions"><button className="button button--secondary" type="button" onClick={() => setEditing(false)}>Отмена</button><button className="button button--primary" type="submit" disabled={saving}>{saving ? 'Сохраняем…' : 'Сохранить профиль'}</button></div>
        </form>}
      </article>
    </div>
  )
}
function PageShell({ children, className = '' }) {
  return <div className={`page-shell container ${className}`.trim()}>{children}</div>
}

function PageHero({ kicker, title, text, panda, children }) {
  return (
    <section className="page-hero">
      <div><p className="eyebrow">{kicker?.replace(/^\d+\.\s*/, '')}</p><h1>{title}</h1><p>{text}</p>{children}</div>
      <div className="page-hero__art"><div className="page-hero__orb" /><RedPanda variant={panda} /></div>
    </section>
  )
}

function CourseFilters({ labels = catalogFilters, active = 'all', query = '', onActiveChange, onQueryChange }) {
  const items = labels.map((item, index) => (typeof item === 'string' ? { label: item, value: index === 0 ? 'all' : item } : item))
  return (
    <div className="filters">
      <label className="search-field"><Icon name="search" /><input value={query} onChange={(event) => onQueryChange?.(event.target.value)} placeholder="Поиск по предметам..." /></label>
      <div className="filter-tags">{items.map((item) => <button key={item.value} className={active === item.value ? 'is-active' : ''} type="button" onClick={() => onActiveChange?.(item.value)}>{item.label}</button>)}</div>
    </div>
  )
}

function ToggleTabs({ items, active, onChange }) {
  return (
    <div className="toggle-tabs">
      {items.map((item, index) => {
        const normalized = typeof item === 'string' ? { label: item, value: item } : item
        const isActive = active ? active === normalized.value : index === 0
        return <button key={normalized.value} className={isActive ? 'is-active' : ''} type="button" onClick={() => onChange?.(normalized.value)}>{normalized.label}</button>
      })}
    </div>
  )
}

function SubjectGrid({ subjects, onSubjectSelect }) {
  return (
    <div className="subject-grid">
      {subjects.map((subject) => (
        <article key={subject.slug ?? subject.title} className="subject-card" role="button" tabIndex="0" onClick={() => onSubjectSelect?.(subject)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSubjectSelect?.(subject) } }}>
          <Icon name={subject.icon} /><h3>{subject.title}</h3><p>{subject.subtitle}</p>{subject.price && <b>{subject.price}</b>}
        </article>
      ))}
    </div>
  )
}

function TrackGrid({ tracks, onTrackSelect }) {
  return (
    <div className="track-grid">
      {tracks.map((track) => (
        <article key={track.slug ?? track.title} className="track-card" role="button" tabIndex="0" onClick={() => onTrackSelect?.(track)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onTrackSelect?.(track) } }}>
          <Icon name={track.icon} /><div><h3>{track.title}</h3><p>{track.text}</p>{track.price && <b>{track.price}</b>}</div>
        </article>
      ))}
    </div>
  )
}

function MiniStats() {
  return <div className="mini-stats">{stats.slice(1).map((item) => <article key={item.label}><Icon name={item.icon} /><b>{item.value}</b><span>{item.label}</span></article>)}</div>
}

function DarkCta({ onNavigate, title, text, action = 'Начать бесплатно', onAction }) {
  return <section className="dark-cta"><RedPanda variant="peek" /><div><h2>{title}</h2><p>{text}</p></div>{onAction ? <button type="button" className="button button--primary" onClick={onAction}>{action}</button> : <SmartLink href="/teachers" onNavigate={onNavigate} className="button button--primary">{action}</SmartLink>}</section>
}

function Footer({ onNavigate }) {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand"><Logo onClick={() => onNavigate('/')} /><p>© 2026 idioma.<br />Все права защищены.</p></div>
        <div className="footer__links">{navItems.map((item) => <SmartLink key={item.href} href={item.href} onNavigate={onNavigate}>{item.label}</SmartLink>)}</div>
        <div className="footer__contacts"><a href="tel:+79832877160">8 983 287 71 60</a><a href="mailto:info@idioma.online">info@idioma.online</a></div>
      </div>
    </footer>
  )
}

const routes = {
  '/': HomePage,
  '/catalog': CatalogPage,
  '/exams': ExamsPage,
  '/programming': ProgrammingPage,
  '/languages': LanguagesPage,
  '/teachers': TeachersPage,
  '/reviews': ReviewsPage,
  '/login': LoginPage,
  '/dashboard': DashboardPage,
}

export default App
