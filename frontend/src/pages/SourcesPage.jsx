import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';

// A small, reusable component for the main status indicator (dot)
const StatusIndicator = ({ status }) => {
  if (status === 'running') {
    return <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" title="Running"></div>;
  }
  if (status === 'completed') {
    return <div className="w-3 h-3 bg-green-500 rounded-full" title="Completed"></div>;
  }
  if (status === 'failed') {
    return <div className="w-3 h-3 bg-red-500 rounded-full" title="Failed"></div>;
  }
  return <div className="w-3 h-3 bg-gray-400 rounded-full" title="Pending"></div>;
};

// A component to render the detailed steps for an active job
const JobProgressDetails = ({ steps }) => {
  if (!steps || steps.length === 0) {
    return null;
  }

  const getStepIcon = (status) => {
    switch (status) {
      case 'running':
        return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>;
      case 'completed':
        return <span className="text-green-500 font-bold">✓</span>;
      case 'failed':
        return <span className="text-red-500 font-bold">✗</span>;
      case 'pending':
      default:
        return <span className="text-gray-400 font-bold">●</span>;
    }
  };

  return (
    <div className="mt-2 pl-5 border-l-2 border-gray-200 space-y-1">
      {steps.map((step, index) => (
        <div key={index} className="flex items-center space-x-2 text-sm">
          <div className="w-5 flex-shrink-0 flex items-center justify-center">{getStepIcon(step.status)}</div>
          <span className={step.status === 'running' ? 'text-gray-800 font-semibold' : 'text-gray-500'}>
            {step.name}
          </span>
          {step.detail && (
            <span className="text-gray-400 ml-2">{step.detail}</span>
          )}
        </div>
      ))}
    </div>
  );
};

function SourcesPage() {
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState('');
  const [maxDepth, setMaxDepth] = useState('');
  const [sources, setSources] = useState([]);
  const [jobs, setJobs] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const intervalRef = useRef(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await axios.get('/api/config');
        setMaxPages(response.data.crawl_default_max_pages);
        setMaxDepth(response.data.crawl_default_max_depth);
      } catch (err) {
        console.error("Failed to fetch app config. Using fallback defaults.");
        setMaxPages(20);
        setMaxDepth(2);
      }
    };
    fetchConfig();
  }, []);

  const fetchSources = async () => {
    try {
      const response = await axios.get('/api/sources');
      setSources(response.data.sources || []);
      setError(null);
    } catch (err) {
      if (!isInitialLoad) {
        setError('Failed to fetch sources. Please ensure the backend is running and refresh.');
      }
    } finally {
      setIsInitialLoad(false);
    }
  };

  const pollJobStatuses = async () => {
    const activeJobs = Object.keys(jobs).filter(
      jobId => jobs[jobId].status === 'pending' || jobs[jobId].status === 'running'
    );

    if (activeJobs.length === 0) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      return;
    }
    
    for (const jobId of activeJobs) {
      try {
        const response = await axios.get(`/api/ingestion_status/${jobId}`);
        const jobData = response.data;
        
        setJobs(prev => ({ ...prev, [jobId]: jobData }));

        if (jobData.status === 'completed' || jobData.status === 'failed') {
          fetchSources();
        }
      } catch (err) {
        console.error(`Failed to get status for job ${jobId}`);
      }
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  useEffect(() => {
    const hasActiveJobs = Object.values(jobs).some(j => j.status === 'pending' || j.status === 'running');
    if (hasActiveJobs && !intervalRef.current) {
      intervalRef.current = setInterval(pollJobStatuses, 2000);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobs]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim() || !maxPages || !maxDepth) {
        toast.warn("Please fill in all fields.");
        return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/crawl', { 
        urls: [url],
        max_pages: Number(maxPages),
        max_depth: Number(maxDepth)
      });
      
      const { job_id, message, status } = response.data;

      if (status === 'skipped') {
        toast.success(message);
      } else {
        toast.info(message);
        if (job_id) {
            setJobs(prev => ({ 
                ...prev, 
                [job_id]: { 
                    status: 'pending', 
                    main_progress: 'Waiting for job to start...',
                    sub_steps: [] 
                } 
            }));
        }
      }
      setUrl('');
    } catch (err) {
      const errorMsg = 'Failed to start ingestion. Is the backend running?';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    if (window.confirm("Are you sure you want to delete the entire knowledge base? This action cannot be undone.")) {
        try {
            const response = await axios.post('/api/reset_knowledge_base');
            toast.success(response.data.message);
            setJobs({});
            fetchSources();
        } catch (err) {
            toast.error("Failed to reset knowledge base.");
        }
    }
  };

  const displayList = [...sources];
  const activeJobIds = Object.keys(jobs);
  
  activeJobIds.forEach(jobId => {
    const job = jobs[jobId];
    if (job.status === 'pending' || job.status === 'running') {
        displayList.unshift({ 
            title: job.main_progress,
            url: jobId, 
            isJob: true, 
            status: job.status,
            sub_steps: job.sub_steps
        });
    }
  });

  return (
    <div className="bg-white p-6 rounded-lg shadow-md max-w-4xl mx-auto animate-fadeIn">
      <h1 className="text-3xl font-bold mb-2">Sources</h1>
      <p className="text-gray-600 mb-6">Add website URLs to build your knowledge base.</p>
      
      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        <div className="flex items-center space-x-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            required
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition-all duration-200 flex items-center justify-center"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              'Add Source'
            )}
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="maxPages" className="block text-sm font-medium text-gray-700 mb-1">
              Max Pages
            </label>
            <input
              type="number"
              id="maxPages"
              value={maxPages}
              onChange={(e) => setMaxPages(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              min="1"
            />
            <p className="text-xs text-gray-500 mt-1">Total number of pages to crawl.</p>
          </div>
          <div>
            <label htmlFor="maxDepth" className="block text-sm font-medium text-gray-700 mb-1">
              Max Depth
            </label>
            <input
              type="number"
              id="maxDepth"
              value={maxDepth}
              onChange={(e) => setMaxDepth(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              min="0"
            />
            <p className="text-xs text-gray-500 mt-1">How many "clicks" deep to go from the start URL.</p>
          </div>
        </div>
      </form>

      {error && <p className="text-red-500 mb-4">{error}</p>}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Knowledge Base</h2>
        <button
          onClick={handleReset}
          className="px-4 py-2 bg-red-600 text-white font-semibold text-sm rounded-lg hover:bg-red-700 disabled:bg-red-300 transition-colors"
        >
          Reset All Data
        </button>
      </div>
      
      <div className="space-y-3">
        {isInitialLoad && sources.length === 0 && (
          <p className="text-gray-500">Loading sources...</p>
        )}
        {!isInitialLoad && sources.length === 0 && Object.keys(jobs).length === 0 && (
          <p className="text-gray-500">Your knowledge base is empty. Add a source to get started.</p>
        )}
        {displayList.map((source, index) => (
          <div key={source.url || index} className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:shadow-sm transition-shadow">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 overflow-hidden">
                <div className="flex-shrink-0">
                  <StatusIndicator status={source.isJob ? source.status : 'completed'} />
                </div>
                <div className="overflow-hidden">
                  <p className="font-semibold text-gray-800 truncate">{source.title}</p>
                  <a href={source.isJob ? undefined : source.url} target="_blank" rel="noopener noreferrer" className={`text-sm text-gray-500 truncate ${source.isJob ? 'cursor-default' : 'hover:underline'}`}>
                    {source.isJob ? `Job ID: ${source.url.substring(0, 8)}...` : source.url}
                  </a>
                </div>
              </div>
            </div>
            {source.isJob && <JobProgressDetails steps={source.sub_steps} />}
          </div>
        ))}
      </div>
    </div>
  );
}

export default SourcesPage;