import pandaWaving from '../assets/panda/01_panda_waving.png';
import pandaLaptop from '../assets/panda/02_panda_laptop.png';
import pandaBook from '../assets/panda/03_panda_reading_book.png';
import pandaPointing from '../assets/panda/04_panda_pointing.png';
import pandaHeadset from '../assets/panda/05_panda_headset.png';
import pandaCertificate from '../assets/panda/06_panda_certificate.png';
import pandaCalendar from '../assets/panda/07_panda_calendar.png';
import pandaBackpack from '../assets/panda/08_panda_backpack.png';
import pandaTeacher from '../assets/panda/09_panda_teacher_board.png';
import pandaTrophy from '../assets/panda/10_panda_trophy.png';
import pandaAuth from '../assets/panda/reg_panda.png';

const pandas = {
  auth: pandaAuth,
  reg: pandaAuth,
  register: pandaAuth,
  peek: pandaWaving,
  wave: pandaWaving,
  waving: pandaWaving,
  laptop: pandaLaptop,
  book: pandaBook,
  books: pandaBook,
  reading: pandaBook,
  pointing: pandaPointing,
  code: pandaPointing,
  headset: pandaHeadset,
  globe: pandaHeadset,
  certificate: pandaCertificate,
  calendar: pandaCalendar,
  backpack: pandaBackpack,
  teacher: pandaTeacher,
  trophy: pandaTrophy,
};

export function RedPanda({ variant = 'laptop', className = '' }) {
  return (
    <img
      className={`red-panda red-panda--${variant} ${className}`}
      src={pandas[variant] ?? pandaLaptop}
      alt="Красная панда idioma"
      loading="eager"
    />
  );
}
