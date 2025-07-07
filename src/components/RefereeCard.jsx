// src/components/RefereeCard.jsx
import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";

const RefereeCard = ({ type = "red", show = false }) => {
  useEffect(() => {
    if (show) {
      const audio = new Audio("/Sound Effects/whistle.mp3");
      audio.play().catch((err) => console.error("Audio play error:", err));
    }
  }, [show]);

  const imageSrc =
    type === "red"
      ? "/Images/ref_red.png"
      : "/Images/ref_yellow.png";

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed inset-0 z-[999] flex justify-center items-center"
          initial={{ x: "-100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "-100%", opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          <img
            src={imageSrc}
            alt={`${type} card referee`}
            className="w-48 sm:w-64 h-auto"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RefereeCard;
