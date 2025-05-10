import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import StudentChatbotIntro from './components/StudentChatbotIntro';
import StoryCanvas from './components/StoryCanvas';

function App() {
  const [appState, setAppState] = useState('intro');
  const [storyData, setStoryData] = useState(null);
  const [studentAnswers, setStudentAnswers] = useState(null);
  const [character, setCharacter] = useState('adventurer');

  const handleIntroComplete = (data) => {
    setStudentAnswers(data.answers);
    setCharacter(data.character);
    setStoryData(data.storyData);
    setAppState('story');
  };

  const handleStoryProgress = async (choice) => {
    try {
      const response = await fetch('http://localhost:5000/api/progress-story', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          choice,
          currentStory: storyData,
          character
        }),
      });
      const nextScene = await response.json();
      setStoryData(nextScene);
    } catch (error) {
      console.error('Error progressing story:', error);
    }
  };

  // Debug: Skip intro and generate a story immediately
  const handleDebugSkip = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/generate-story', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          storyContext: 'fantasy world',
          character: 'adventurer'
        }),
      });
      const data = await response.json();
      setCharacter('adventurer');
      setStoryData(data);
      setAppState('story');
    } catch (error) {
      console.error('Error skipping intro:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 to-purple-900 text-white p-8">
      <AnimatePresence mode="wait">
        {appState === 'intro' ? (
          <motion.div
            key="intro"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {/* Debug Skip Button */}
            <button
              onClick={handleDebugSkip}
              className="mb-6 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-bold rounded shadow-lg"
            >
              Debug: Skip Intro & Start Story
            </button>
            <StudentChatbotIntro onComplete={handleIntroComplete} />
          </motion.div>
        ) : (
          <motion.div
            key="story"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <StoryCanvas 
              scene={storyData} 
              onChoice={handleStoryProgress}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App; 