import logo from '../assets/logo/logo.png';

export function Logo({ compact = false, onClick }) {
  return (
    <a
      className={`brand ${compact ? 'brand--compact' : ''}`}
      href="/"
      aria-label="idioma home"
      onClick={(event) => {
        if (onClick) {
          event.preventDefault();
          onClick(event);
        }
      }}
    >
      <img className="brand__image" src={logo} alt="idioma" />
    </a>
  );
}
