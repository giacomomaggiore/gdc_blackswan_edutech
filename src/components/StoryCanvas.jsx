import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import React from 'react';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

const optionVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
  hover: { 
    scale: 1.02,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    transition: { duration: 0.2 }
  },
  tap: { 
    scale: 0.98,
    transition: { duration: 0.1 }
  }
};

function StoryCanvas({ scene, onChoice }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [currentScene, setCurrentScene] = useState(scene);

  useEffect(() => {
    setCurrentScene(scene);
    setSelectedOption(null);
    setShowFeedback(false);
    setFeedback("");
  }, [scene]);

  const handleOptionClick = async (option) => {
    setSelectedOption(option);
    setIsSubmitting(true);
    // Await the next scene from parent
    const nextScene = await onChoice(option);
    // If backend returns feedback, show it, then auto-progress
    if (nextScene && nextScene.feedback) {
      setFeedback(nextScene.feedback);
      setShowFeedback(true);
      setTimeout(() => {
        setShowFeedback(false);
        setIsSubmitting(false);
        setFeedback("");
        setSelectedOption(null);
        setCurrentScene(nextScene);
      }, 1800);
    } else {
      setIsSubmitting(false);
      setSelectedOption(null);
      setCurrentScene(nextScene || scene);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-900 via-purple-800 to-pink-700 py-12 px-2">
      {/* Loading Overlay */}
      <AnimatePresence>
        {isSubmitting && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="flex flex-col items-center"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
            >
              <motion.div
                className="w-16 h-16 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin mb-4"
                animate={{ rotate: 360 }}
                transition={{ 
                  duration: 1.5, 
                  repeat: Infinity, 
                  ease: "linear",
                  repeatType: "loop"
                }}
              />
              <span className="text-white text-lg font-semibold drop-shadow-lg">Thinking...</span>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl w-full mx-auto bg-white/10 backdrop-blur-lg rounded-3xl p-10 shadow-2xl space-y-8 border-2 border-white/20"
        style={{ minHeight: '70vh' }}
      >
        {/* Progress Bar */}
        {typeof currentScene.progress === 'number' && (
          <motion.div 
            className="w-full h-3 bg-white/30 rounded-full mb-6 overflow-hidden"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <motion.div
              className="h-full bg-gradient-to-r from-pink-500 via-indigo-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${Math.round(currentScene.progress * 100)}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          </motion.div>
        )}

        <motion.div 
          className="space-y-8"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {/* Scene Image */}
          {currentScene.imageRef && (
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ 
                type: "spring",
                stiffness: 100,
                damping: 15,
                delay: 0.2 
              }}
              className="relative aspect-video rounded-lg overflow-hidden shadow-lg border border-white/20"
            >
              <motion.img
                src={currentScene.imageRef}
                alt="Scene illustration"
                className="w-full h-full object-cover"
                initial={{ scale: 1.1 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5 }}
              />
            </motion.div>
          )}

          {/* Scene Text */}
          {!currentScene.finished && (
            <motion.p
              variants={fadeInUp}
              className="text-lg leading-relaxed text-white drop-shadow-md bg-gradient-to-r from-indigo-800/60 to-pink-700/40 p-6 rounded-xl border border-white/10"
            >
              {currentScene.sceneText}
            </motion.p>
          )}

          {/* Feedback */}
          <AnimatePresence>
            {showFeedback && feedback && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ type: "spring", stiffness: 200, damping: 20 }}
                className="mt-2 p-4 rounded-lg text-center font-semibold shadow-md border-2 bg-blue-500/30 border-blue-400/40 text-blue-900"
              >
                {feedback}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Multiple Choice Question */}
          {!currentScene.finished
            && Array.isArray(currentScene.questions)
            && currentScene.questions.length > 0
            && (() => {
              const q = currentScene.questions[0];
              return (
                <motion.div
                  variants={fadeInUp}
                  className="space-y-4"
                >
                  <motion.h3 
                    className="text-xl font-semibold mb-2 text-white drop-shadow"
                    variants={fadeInUp}
                  >
                    {q.prompt}
                  </motion.h3>
                  <motion.div 
                    className="space-y-3"
                    variants={staggerContainer}
                  >
                    {q.choices.map((option, idx) => (
                      <motion.button
                        key={idx}
                        variants={optionVariants}
                        whileHover="hover"
                        whileTap="tap"
                        onClick={() => handleOptionClick(option)}
                        disabled={isSubmitting || selectedOption !== null}
                        className={`w-full p-4 text-left rounded-lg transition-colors bg-white/20 hover:bg-white/30 border-white/30 border font-semibold text-indigo-900 shadow-md text-lg ${
                          selectedOption === option ? 'bg-indigo-600 text-white border-indigo-400' : ''
                        }`}
                      >
                        {option}
                      </motion.button>
                    ))}
                  </motion.div>
                </motion.div>
              );
            })()}

          {/* End of Story / Score Summary */}
          {currentScene.finished && (
            <motion.div 
              className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 bg-gradient-to-br from-indigo-900 via-purple-800 to-pink-700 rounded-3xl shadow-2xl p-10"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 100, damping: 15 }}
            >
              <span className="inline-block bg-yellow-400 text-white rounded-full p-8 text-6xl shadow-lg mb-2">🏆</span>
              <h2 className="text-4xl font-extrabold mb-2 text-white drop-shadow">Adventure Complete!</h2>
              <p className="text-2xl text-white mb-2">Your final score: <span className="font-bold">{currentScene.score}</span></p>

              {/* Schematic Journey Grid */}
              {currentScene.metaphors && currentScene.metaphors.length > 0 && (
                <div className="w-full max-w-4xl grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-6">
                  {currentScene.metaphors.map((metaphor, index) => (
                    <div key={index} className="bg-white/20 rounded-2xl p-6 flex flex-col items-center shadow-lg border-2 border-white/20">
                      <div className="text-3xl font-bold text-indigo-400 mb-2">{index + 1}</div>
                      <div className="text-lg text-pink-200 font-semibold mb-2 text-center">{currentScene.mathConcepts[index]}</div>
                      <div className="italic text-white text-center">{metaphor}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Principle Summary */}
              {currentScene.principleSummary && (
                <div className="w-full max-w-2xl bg-yellow-100/20 rounded-xl p-6 border-2 border-yellow-300 mt-8">
                  <h3 className="text-xl font-bold text-yellow-300 mb-2 text-center">
                    Main Mathematical Principle
                  </h3>
                  <div className="prose prose-invert prose-p:text-yellow-100 prose-strong:text-yellow-300 mx-auto text-center">
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {currentScene.principleSummary}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {currentScene.theorySummary && (
                <div className="w-full max-w-2xl bg-white/10 rounded-xl p-6 border border-white/20 mt-8">
                  <h3 className="text-2xl font-bold text-indigo-200 mb-4 text-center">What You Learned</h3>
                  <div className="prose prose-invert prose-p:text-white prose-strong:text-pink-300 prose-em:text-indigo-200 mx-auto">
                    <ReactMarkdown>{currentScene.theorySummary}</ReactMarkdown>
                  </div>
                </div>
              )}
              <button
                className="mt-8 px-8 py-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xl font-bold rounded-full shadow-lg transition-colors"
                onClick={() => window.location.reload()}
              >
                Play Again
              </button>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}

export default StoryCanvas; 