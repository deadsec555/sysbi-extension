// This script runs on the Sysbi CRM pages
console.log("Sysbi CRM Intelligence Extension Active");

// Example: Scrape lead data from the page and send to dashboard
function scrapeLeads() {
  const leads = [];
  const rows = document.querySelectorAll('.lead-row'); // Adjust selector based on actual CRM
  rows.forEach(row => {
    leads.push({
      name: row.querySelector('.name')?.innerText,
      status: row.querySelector('.status')?.innerText,
      notes: row.querySelector('.notes')?.innerText
    });
  });
  return leads;
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getLeads") {
    sendResponse({ leads: scrapeLeads() });
  }
});
