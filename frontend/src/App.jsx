const handleStoryProgress = async (choice) => {
  try {
    // Transform storyData to match backend's expected structure
    const transformedScene = {
      sceneText: storyData.sceneText || '',
      imageRef: storyData.imageRef || '',
      progress: storyData.progress || 0,
      questions: (storyData.questions || []).map(q => ({
        prompt: q.prompt || '',
        choices: q.choices || [],
        answer: q.answer || '',
        feedback: q.feedback || ''
      })),
      metaphor: storyData.metaphor || '',
      mathConcept: storyData.mathConcept || '',
      finished: storyData.finished || false,
      score: storyData.score || 0,
      step: storyData.step || 0,
      answers: storyData.answers || [],
      metaphors: storyData.metaphors || [],
      mathConcepts: storyData.mathConcepts || [],
      storyHistory: storyData.storyHistory || []
    };

    const response = await fetch('http://localhost:5000/api/progress-story', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        choice,
        currentScene: transformedScene,
        storyContext,
        character,
        mathTopic: storyData?.mathTopic || storyData?.math_topic || 'algebra'
      }),
    });
    const nextScene = await response.json();
    setStoryData(nextScene);
  } catch (error) {
    console.error('Error progressing story:', error);
  }
}; 