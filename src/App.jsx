import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import StudentChatbotIntro from './components/StudentChatbotIntro';
import StoryCanvas from './components/StoryCanvas';

function App() {
  const [appState, setAppState] = useState('intro');
  const [storyData, setStoryData] = useState(null);
  const [studentAnswers, setStudentAnswers] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const handleIntroComplete = (data) => {
    setStudentAnswers(data.answers);
    setStoryData(data.storyData);
    setSessionId(data.storyData.sessionId);
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
          sessionId,
          choice
        }),
      });
      
      const nextScene = await response.json();
      setStoryData(nextScene);
    } catch (error) {
      console.error('Error progressing story:', error);
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