import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function StoryCanvas({ scene, onChoice }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [lastFeedback, setLastFeedback] = useState("");

  const handleOptionClick = async (option) => {
    setSelectedOption(option);
    setIsSubmitting(true);
    const result = await onChoice(option);
    setIsSubmitting(false);
    setShowFeedback(true);
    setLastFeedback(scene.feedback || "");
    setTimeout(() => {
      setShowFeedback(false);
      setSelectedOption(null);
    }, 1800);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-4xl mx-auto"
    >
      {/* Progress Bar */}
      {typeof scene.progress === 'number' && (
        <div className="w-full h-3 bg-white/20 rounded-full mb-6 overflow-hidden">
          <div
            className="h-full bg-indigo-500 transition-all"
            style={{ width: `${Math.round(scene.progress * 100)}%` }}
          ></div>
        </div>
      )}

      <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl space-y-8">
        {/* Scene Image */}
        {scene.imageRef && (
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="relative aspect-video rounded-lg overflow-hidden"
          >
            <img
              src={scene.imageRef}
              alt="Scene illustration"
              className="w-full h-full object-cover"
            />
          </motion.div>
        )}

        {/* Scene Text */}
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-lg leading-relaxed"
        >
          {scene.sceneText}
        </motion.p>

        {/* Feedback */}
        <AnimatePresence>
          {scene.feedback && showFeedback && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className={`mt-2 p-4 rounded-lg text-center font-semibold ${scene.feedback.includes('Correct') ? 'bg-green-500/20' : 'bg-red-500/20'}`}
            >
              {scene.feedback}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Multiple Choice Question */}
        {!scene.finished && scene.question && scene.options && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="space-y-4"
          >
            <h3 className="text-xl font-semibold mb-2">{scene.question}</h3>
            <div className="space-y-3">
              {scene.options.map((option, idx) => (
                <motion.button
                  key={idx}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleOptionClick(option)}
                  disabled={isSubmitting || selectedOption !== null}
                  className={`w-full p-4 text-left rounded-lg transition-colors bg-white/5 hover:bg-white/10 border-white/20 border font-semibold ${selectedOption === option ? 'bg-indigo-600 text-white' : ''}`}
                >
                  {option}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* End of Story / Score Summary */}
        {scene.finished && (
          <div className="text-center space-y-4">
            <h2 className="text-2xl font-bold">Adventure Complete!</h2>
            <p className="text-lg">Your final score: <span className="font-bold">{scene.score}</span></p>
            <p className="text-lg">Thanks for playing!</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default StoryCanvas; 