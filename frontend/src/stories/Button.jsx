// ;
import PropTypes from 'prop-types'

// Raw CSS removed in favor of Tailwind
// import './button.css';

/** Primary UI component for user interaction */
export const Button = ({
  primary = false,
  backgroundColor = null,
  size = 'medium',
  label,
  ...props
}) => {
  // Tailwind mapping
  const baseClasses = 'font-bold border-0 rounded-3xl cursor-pointer inline-block leading-none'
  const modeClasses = primary
    ? 'text-white bg-[#1ea7fd]'
    : 'text-[#333] bg-transparent shadow-[rgba(0,0,0,0.15)_0px_0px_0px_1px_inset]'

  const sizeClasses = {
    small: 'text-xs py-2.5 px-4',
    medium: 'text-sm py-3 px-5',
    large: 'text-base py-4 px-6',
  }

  return (
    <button
      type="button"
      className={`${baseClasses} ${sizeClasses[size]} ${modeClasses}`}
      style={backgroundColor && { backgroundColor }}
      {...props}
    >
      {label}
    </button>
  )
}

Button.propTypes = {
  /** Is this the principal call to action on the page? */
  primary: PropTypes.bool,
  /** What background color to use */
  backgroundColor: PropTypes.string,
  /** How large should the button be? */
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  /** Button contents */
  label: PropTypes.string.isRequired,
  /** Optional click handler */
  onClick: PropTypes.func,
}
