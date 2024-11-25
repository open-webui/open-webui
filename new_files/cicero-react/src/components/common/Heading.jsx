import PropTypes from 'prop-types';

const Heading = ({
    title,
    description = null,
    descriptionBold = null,
    className = "",
}) => {
    return (
        <>
            <h1
                className={`mt-[30px] text-center uppercase font-sans text-4xl md:text-5xl lg:text-6xl font-bold leading-[60px] text-[var(--text-primary)] ${className}`}
            >
                {title}
            </h1>
            {(description || descriptionBold) && (
                <p className="font-sans text-center text-base font-normal leading-[30px] mt-2 text-[var(--text-secondary)]">
                    {description}{" "}
                    <span className="font-bold text-[var(--text-primary)]">{descriptionBold}</span>
                </p>
            )}
        </>
    );
};

Heading.propTypes = {
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    descriptionBold: PropTypes.string,
    className: PropTypes.string
};

export default Heading;
