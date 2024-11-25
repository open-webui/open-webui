/* eslint-disable react/prop-types */
import { motion } from "framer-motion";

const ReavealAnimationProvider = ({
    topOrBottm = 0,
    leftOrRight = 0,
    children,
}) => {
    return (
        <motion.div
            initial={{ x: leftOrRight, y: topOrBottm }}
            whileInView={{ x: 0, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            {children}
        </motion.div>
    );
};

export default ReavealAnimationProvider;
