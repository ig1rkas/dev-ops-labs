import homeIcon from '../assets/icons/01_icon_home.png';
import searchIcon from '../assets/icons/02_icon_search.png';
import filterIcon from '../assets/icons/03_icon_filter.png';
import menuIcon from '../assets/icons/04_icon_menu.png';
import closeIcon from '../assets/icons/05_icon_close.png';
import arrowRightIcon from '../assets/icons/06_icon_arrow_right.png';
import calendarIcon from '../assets/icons/09_icon_calendar.png';
import clockIcon from '../assets/icons/10_icon_clock.png';
import bellIcon from '../assets/icons/11_icon_bell.png';
import chatIcon from '../assets/icons/12_icon_chat.png';
import profileIcon from '../assets/icons/13_icon_profile.png';
import groupIcon from '../assets/icons/14_icon_group.png';
import starsIcon from '../assets/icons/15_icon_rating_stars.png';
import heartIcon from '../assets/icons/16_icon_heart.png';
import checkIcon from '../assets/icons/17_icon_check.png';
import playIcon from '../assets/icons/18_icon_play.png';
import settingsIcon from '../assets/icons/21_icon_settings.png';
import documentIcon from '../assets/icons/22_icon_document.png';
import bookIcon from '../assets/icons/23_icon_book.png';
import graduationIcon from '../assets/icons/24_icon_graduation_cap.png';
import mathSigmaIcon from '../assets/icons/01_icon_math_sigma.png';
import languageIcon from '../assets/icons/02_icon_language_ab.png';
import booksStackIcon from '../assets/icons/03_icon_books_stack.png';
import chemistryFlaskIcon from '../assets/icons/04_icon_chemistry_flask.png';
import physicsAtomIcon from '../assets/icons/05_icon_physics_atom.png';
import biologyDnaIcon from '../assets/icons/06_icon_biology_dna.png';
import historyColumnIcon from '../assets/icons/07_icon_history_column.png';
import geographyGlobeIcon from '../assets/icons/08_icon_geography_globe.png';
import programmingCodeIcon from '../assets/icons/09_icon_programming_code.png';
import terminalIcon from '../assets/icons/10_icon_terminal.png';
import webCodeWindowIcon from '../assets/icons/11_icon_web_code_window.png';
import gamepadIcon from '../assets/icons/12_icon_gamepad.png';
import networkNodesIcon from '../assets/icons/13_icon_network_nodes.png';
import robotAiIcon from '../assets/icons/14_icon_robot_ai.png';
import egeExamSheetIcon from '../assets/icons/15_icon_ege_exam_sheet.png';
import ogeShieldIcon from '../assets/icons/16_icon_oge_shield.png';
import ieltsGlobeIcon from '../assets/icons/17_icon_ielts_globe.png';
import toeflCertificateIcon from '../assets/icons/18_icon_toefl_certificate.png';
import hskChineseIcon from '../assets/icons/19_icon_hsk_chinese.png';
import japaneseSakuraIcon from '../assets/icons/20_icon_japanese_sakura.png';
import deleBadgeIcon from '../assets/icons/21_icon_dele_badge.png';
import certificateRibbonIcon from '../assets/icons/22_icon_certificate_ribbon.png';
import targetArrowIcon from '../assets/icons/23_icon_target_arrow.png';
import growthChartIcon from '../assets/icons/24_icon_growth_chart.png';

const icons = {
  home: homeIcon,
  search: searchIcon,
  filter: filterIcon,
  menu: menuIcon,
  close: closeIcon,
  arrow: arrowRightIcon,
  calendar: calendarIcon,
  clock: clockIcon,
  bell: bellIcon,
  chat: chatIcon,
  profile: profileIcon,
  users: groupIcon,
  group: groupIcon,
  people: groupIcon,
  stars: starsIcon,
  star: starsIcon,
  rating: starsIcon,
  heart: heartIcon,
  check: checkIcon,
  play: playIcon,
  settings: settingsIcon,
  document: documentIcon,
  exam: egeExamSheetIcon,
  lesson: documentIcon,
  plan: documentIcon,
  book: bookIcon,
  books: booksStackIcon,
  language: languageIcon,
  graduation: graduationIcon,
  badge: certificateRibbonIcon,
  certificate: certificateRibbonIcon,
  flask: chemistryFlaskIcon,
  physics: physicsAtomIcon,
  biology: biologyDnaIcon,
  globe: geographyGlobeIcon,
  history: historyColumnIcon,
  code: programmingCodeIcon,
  web: webCodeWindowIcon,
  sum: mathSigmaIcon,
  sigma: mathSigmaIcon,
  game: gamepadIcon,
  python: terminalIcon,
  terminal: terminalIcon,
  network: networkNodesIcon,
  robot: robotAiIcon,
  oge: ogeShieldIcon,
  ielts: ieltsGlobeIcon,
  toefl: toeflCertificateIcon,
  hsk: hskChineseIcon,
  jlpt: japaneseSakuraIcon,
  dele: deleBadgeIcon,
  clipboard: documentIcon,
  chart: growthChartIcon,
  target: targetArrowIcon,
};

export function Icon({ name, className = '', size = 24 }) {
  const src = icons[name] ?? starsIcon;

  return (
    <img
      className={`icon asset-icon ${className}`}
      src={src}
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
      loading="eager"
    />
  );
}
