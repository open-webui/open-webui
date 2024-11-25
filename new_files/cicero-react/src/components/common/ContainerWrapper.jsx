/* eslint-disable react/prop-types */
function ContainerWrapper({ children, className }) {
    return (
        <div
            className={`w-full max-w-[1440px] mx-auto px-3 sm:px-6 md:px-8 lg:px-[49px] ${className} overflow-hidden`}
        >
            {children}
        </div>
    );
}

export default ContainerWrapper;
