/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, LineChart, Line, Legend 
} from 'recharts';
import { 
  Users, Phone, TrendingUp, AlertCircle, CheckCircle2, 
  Clock, Search, Filter, Download, User, MessageSquare,
  ArrowUpRight, Calendar, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Lead, analyzeLeads } from './services/gemini';
import { MOCK_LEADS } from './services/mockData';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  const [leads, setLeads] = useState<Lead[]>(MOCK_LEADS);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'hot' | 'agents' | 'extension'>('all');

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const analysis = await analyzeLeads(leads);
      const updatedLeads = leads.map(lead => {
        const result = analysis.find((a: any) => a.id === lead.id);
        if (result) {
          return { ...lead, ...result };
        }
        return lead;
      });
      setLeads(updatedLeads);
    } catch (error) {
      console.error("Analysis failed", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    // Initial analysis if not already done
    if (!leads[0].priority) {
      handleAnalyze();
    }
  }, []);

  const filteredLeads = useMemo(() => {
    let result = leads;
    if (searchTerm) {
      result = result.filter(l => 
        l.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.agentId.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    if (activeTab === 'hot') {
      result = result.filter(l => l.priority === 'Hot');
    }
    return result;
  }, [leads, searchTerm, activeTab]);

  const stats = useMemo(() => {
    const total = leads.length;
    const hot = leads.filter(l => l.priority === 'Hot').length;
    const contactedToday = leads.filter(l => {
      const today = new Date().toISOString().split('T')[0];
      return l.lastContact.startsWith(today);
    }).length;
    const conversionRate = 15.5; // Mocked

    return [
      { label: 'Total Leads', value: total, icon: Users, color: 'text-blue-600' },
      { label: 'Hot Leads', value: hot, icon: TrendingUp, color: 'text-orange-600' },
      { label: 'Contacted Today', value: contactedToday, icon: Phone, color: 'text-green-600' },
      { label: 'Conversion Rate', value: `${conversionRate}%`, icon: CheckCircle2, color: 'text-purple-600' },
    ];
  }, [leads]);

  const chartData = useMemo(() => {
    const statusCounts = leads.reduce((acc: any, lead) => {
      acc[lead.status] = (acc[lead.status] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(statusCounts).map(([name, value]) => ({ name, value }));
  }, [leads]);

  const agentPerformance = useMemo(() => {
    const agents = leads.reduce((acc: any, lead) => {
      if (!acc[lead.agentId]) {
        acc[lead.agentId] = { name: lead.agentId, hot: 0, total: 0 };
      }
      acc[lead.agentId].total += 1;
      if (lead.priority === 'Hot') acc[lead.agentId].hot += 1;
      return acc;
    }, {});

    return Object.values(agents);
  }, [leads]);

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1A1A1A] font-sans">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 z-50 hidden lg:block">
        <div className="p-6 border-bottom border-gray-100">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">S</div>
            <h1 className="text-xl font-bold tracking-tight">Sysbi CRM</h1>
          </div>
          
          <nav className="space-y-1">
            <NavItem icon={TrendingUp} label="Dashboard" active />
            <NavItem icon={Users} label="Leads" />
            <NavItem icon={Phone} label="Call Queue" />
            <NavItem icon={Calendar} label="Schedule" />
            <NavItem icon={MessageSquare} label="Messages" />
            <div className="pt-4 mt-4 border-t border-gray-100">
              <NavItem icon={User} label="Agents (9)" />
              <NavItem 
                icon={Download} 
                label="Extension Setup" 
                onClick={() => setActiveTab('extension')} 
                active={activeTab === 'extension'}
              />
            </div>
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 p-8">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl font-bold">Lead Intelligence Report</h2>
            <p className="text-gray-500 text-sm">AI-powered insights for your sales team</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className={cn(
                "flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium transition-all hover:bg-blue-700 disabled:opacity-50",
                isAnalyzing && "animate-pulse"
              )}
            >
              <RefreshCw className={cn("w-4 h-4", isAnalyzing && "animate-spin")} />
              {isAnalyzing ? 'Analyzing...' : 'Run Daily Report'}
            </button>
            <button className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50">
              <Download className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, i) => (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              key={stat.label} 
              className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={cn("p-2 rounded-lg bg-opacity-10", stat.color.replace('text', 'bg'))}>
                  <stat.icon className={cn("w-6 h-6", stat.color)} />
                </div>
                <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">+12%</span>
              </div>
              <p className="text-gray-500 text-sm font-medium">{stat.label}</p>
              <h3 className="text-2xl font-bold mt-1">{stat.value}</h3>
            </motion.div>
          ))}
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold mb-6">Lead Pipeline Status</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F1F1" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold mb-6">Priority Distribution</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Hot', value: leads.filter(l => l.priority === 'Hot').length },
                      { name: 'Warm', value: leads.filter(l => l.priority === 'Warm').length },
                      { name: 'Cold', value: leads.filter(l => l.priority === 'Cold').length },
                    ]}
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    <Cell fill="#F97316" />
                    <Cell fill="#3B82F6" />
                    <Cell fill="#94A3B8" />
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Leads Table Section */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex bg-gray-100 p-1 rounded-lg">
                <button 
                  onClick={() => setActiveTab('all')}
                  className={cn("px-4 py-1.5 text-sm font-medium rounded-md transition-all", activeTab === 'all' ? "bg-white shadow-sm text-blue-600" : "text-gray-500 hover:text-gray-700")}
                >
                  All Leads
                </button>
                <button 
                  onClick={() => setActiveTab('hot')}
                  className={cn("px-4 py-1.5 text-sm font-medium rounded-md transition-all", activeTab === 'hot' ? "bg-white shadow-sm text-orange-600" : "text-gray-500 hover:text-gray-700")}
                >
                  Hot Leads
                </button>
                <button 
                  onClick={() => setActiveTab('agents')}
                  className={cn("px-4 py-1.5 text-sm font-medium rounded-md transition-all", activeTab === 'agents' ? "bg-white shadow-sm text-blue-600" : "text-gray-500 hover:text-gray-700")}
                >
                  Agent Performance
                </button>
              </div>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input 
                type="text" 
                placeholder="Search leads or agents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full md:w-64"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            {activeTab === 'extension' ? (
              <div className="p-8 max-w-3xl mx-auto">
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 mb-8">
                  <h3 className="text-blue-800 font-bold mb-2 flex items-center gap-2">
                    <Download className="w-5 h-5" />
                    Chrome Extension Integration
                  </h3>
                  <p className="text-blue-700 text-sm">
                    To use Sysbi CRM Intelligence as a Chrome Extension, follow these steps to load the extension files into your browser.
                  </p>
                </div>

                <div className="space-y-6">
                  <Step 
                    number="1" 
                    title="Download Extension Files" 
                    description="Download the manifest.json and content.js files from this project's public folder."
                  />
                  <Step 
                    number="2" 
                    title="Open Extensions Page" 
                    description="Open Chrome and navigate to chrome://extensions"
                  />
                  <Step 
                    number="3" 
                    title="Enable Developer Mode" 
                    description="Toggle the 'Developer mode' switch in the top right corner."
                  />
                  <Step 
                    number="4" 
                    title="Load Unpacked" 
                    description="Click 'Load unpacked' and select the folder containing your extension files."
                  />
                </div>

                <div className="mt-12 p-6 bg-gray-50 rounded-xl border border-gray-200">
                  <h4 className="font-bold mb-4">Extension Features</h4>
                  <ul className="space-y-3 text-sm text-gray-600">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      Automatic lead scraping from Sysbi CRM pages
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      Real-time AI prioritization overlay
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      One-click daily report generation
                    </li>
                  </ul>
                </div>
              </div>
            ) : activeTab === 'agents' ? (
              <table className="w-full text-left">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Agent Name</th>
                    <th className="px-6 py-4 font-semibold">Total Leads</th>
                    <th className="px-6 py-4 font-semibold">Hot Leads</th>
                    <th className="px-6 py-4 font-semibold">Performance Score</th>
                    <th className="px-6 py-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {agentPerformance.map((agent: any) => (
                    <tr key={agent.name} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-xs">
                            {agent.name.split(' ')[1]}
                          </div>
                          <span className="font-medium">{agent.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">{agent.total}</td>
                      <td className="px-6 py-4 text-sm font-medium text-orange-600">{agent.hot}</td>
                      <td className="px-6 py-4">
                        <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden">
                          <div 
                            className="bg-blue-600 h-full rounded-full" 
                            style={{ width: `${(agent.hot / agent.total) * 100}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="text-blue-600 text-sm font-medium hover:underline">View Details</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-left">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Lead Info</th>
                    <th className="px-6 py-4 font-semibold">Status</th>
                    <th className="px-6 py-4 font-semibold">AI Priority</th>
                    <th className="px-6 py-4 font-semibold">Next Action</th>
                    <th className="px-6 py-4 font-semibold">Agent</th>
                    <th className="px-6 py-4 font-semibold text-right">Last Contact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <AnimatePresence mode="popLayout">
                    {filteredLeads.map((lead) => (
                      <motion.tr 
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        key={lead.id} 
                        className="hover:bg-gray-50 transition-colors group"
                      >
                        <td className="px-6 py-4">
                          <div>
                            <div className="font-bold text-sm">{lead.name}</div>
                            <div className="text-xs text-gray-500">{lead.email}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn(
                            "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide",
                            lead.status === 'Negotiation' ? "bg-purple-100 text-purple-700" :
                            lead.status === 'Qualified' ? "bg-blue-100 text-blue-700" :
                            lead.status === 'New' ? "bg-green-100 text-green-700" :
                            "bg-gray-100 text-gray-700"
                          )}>
                            {lead.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {lead.priority ? (
                            <div className="flex items-center gap-2">
                              <span className={cn(
                                "w-2 h-2 rounded-full",
                                lead.priority === 'Hot' ? "bg-orange-500 animate-pulse" :
                                lead.priority === 'Warm' ? "bg-blue-500" : "bg-gray-400"
                              )} />
                              <span className={cn(
                                "text-sm font-bold",
                                lead.priority === 'Hot' ? "text-orange-600" :
                                lead.priority === 'Warm' ? "text-blue-600" : "text-gray-500"
                              )}>
                                {lead.priority}
                              </span>
                              {lead.interestScore && (
                                <span className="text-[10px] text-gray-400 font-mono">({lead.interestScore}%)</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-300 italic">Pending analysis...</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-xs text-gray-600 max-w-[200px] truncate group-hover:whitespace-normal group-hover:overflow-visible group-hover:bg-white group-hover:relative group-hover:z-10">
                            {lead.nextAction || 'No action recommended'}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{lead.agentId}</td>
                        <td className="px-6 py-4 text-right text-xs text-gray-500">
                          {new Date(lead.lastContact).toLocaleDateString()}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>

      {/* Extension Simulation Overlay (Optional Visual) */}
      <div className="fixed bottom-6 right-6 z-[100]">
        <motion.div 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="bg-blue-600 text-white p-4 rounded-full shadow-2xl cursor-pointer flex items-center gap-2"
        >
          <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <span className="font-bold text-sm pr-2">Sysbi Extension Active</span>
        </motion.div>
      </div>
    </div>
  );
}

function NavItem({ icon: Icon, label, active = false, onClick }: { icon: any, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left",
        active ? "bg-blue-50 text-blue-600" : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
      )}
    >
      <Icon className="w-5 h-5" />
      {label}
    </button>
  );
}

function Step({ number, title, description }: { number: string, title: string, description: string }) {
  return (
    <div className="flex gap-4">
      <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold shrink-0">
        {number}
      </div>
      <div>
        <h4 className="font-bold text-gray-900">{title}</h4>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
    </div>
  );
}
