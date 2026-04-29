// ===== STATE =====
let currentQuery = '';
let currentPage = 1;
let totalPages = 1;
let forecastChart = null;

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('navSearchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') triggerSearch();
  });
  document.getElementById('heroSearchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') triggerSearch();
  });
  searchProducts('laptop', 1);
});

function triggerSearch() {
  const navVal = document.getElementById('navSearchInput').value.trim();
  const heroVal = document.getElementById('heroSearchInput').value.trim();
  const q = navVal || heroVal || 'laptop';
  currentQuery = q;
  currentPage = 1;
  searchProducts(q, 1);
}

function quickSearch(brand) {
  currentQuery = brand;
  document.getElementById('navSearchInput').value = brand;
  document.getElementById('heroSearchInput').value = brand;
  searchProducts(brand, 1);
}

function applyFilters() {
  currentPage = 1;
  searchProducts(currentQuery || 'laptop', 1);
}

async function searchProducts(query, page = 1) {
  showSection('results');
  showLoading(true);
  const website  = document.getElementById('filterWebsite').value;
  const sort     = document.getElementById('filterSort').value;
  const minPrice = document.getElementById('minPrice').value || 0;
  const maxPrice = document.getElementById('maxPrice').value || 9999999;
  const params = new URLSearchParams({ q: query, page, per_page: 20, website, sort, min_price: minPrice, max_price: maxPrice });
  try {
    const res  = await fetch('/api/search?' + params);
    const data = await res.json();
    showLoading(false);
    document.getElementById('resultsTitle').textContent = query ? 'Results for "' + query + '"' : 'All Laptops';
    document.getElementById('resultsCount').textContent = data.total.toLocaleString() + ' products found';
    totalPages = data.pages;
    currentPage = data.page;
    renderProducts(data.results);
    renderPagination(data.page, data.pages, query);
  } catch (err) {
    showLoading(false);
    document.getElementById('emptyState').style.display = 'flex';
  }
}

// ===== RENDER =====
function renderProducts(products) {
  const grid  = document.getElementById('productGrid');
  const empty = document.getElementById('emptyState');
  grid.innerHTML = '';
  if (!products || products.length === 0) { empty.style.display = 'flex'; return; }
  empty.style.display = 'none';
  products.forEach((p, i) => grid.appendChild(createProductCard(p, i)));
}

function createProductCard(p, delay) {
  const card = document.createElement('div');
  card.className = 'product-card';
  card.style.animationDelay = (delay * 0.04) + 's';
  const score = p.ai_score || 0;
  card.innerHTML =
    '<div class="card-body">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
        '<span class="card-site-badge ' + getSiteClass(p.website) + '">' + escHtml(p.website||'N/A') + '</span>' +
        buildReviewTag(p.reviews) +
      '</div>' +
      '<div class="card-name">' + escHtml(p.product_name||'N/A') + '</div>' +
      '<div class="card-desc">' + escHtml(p.product_description||'N/A') + '</div>' +
      '<div class="card-meta">' +
        '<div class="card-price"><span class="currency">₹</span>' + (p.price||0).toLocaleString('en-IN') + '</div>' +
        buildRatingHtml(p.ratings_num, p.ratings) +
      '</div>' +
      '<div class="ai-score-wrap">' +
        '<div class="ai-score-label"><span>AI Score</span><span>' + score + '</span></div>' +
        '<div class="ai-score-bar"><div class="ai-score-fill" style="width:' + score + '%"></div></div>' +
      '</div>' +
      '<div class="card-actions">' +
        '<button class="btn-compare" onclick="event.stopPropagation();openCompare(\'' + escAttr(p.product_name) + '\')">Compare</button>' +
        '<button class="btn-predict" onclick="event.stopPropagation();openPredict(\'' + escAttr(p.product_name) + '\')">Forecast</button>' +
        '<button class="btn-view" onclick="window.location=\'/product/' + p.id + '\'">View →</button>' +
      '</div>' +
    '</div>';
  card.addEventListener('click', () => { window.location = '/product/' + p.id; });
  return card;
}

function buildRatingHtml(ratingsNum, ratingsRaw) {
  if (ratingsNum && ratingsNum > 0) {
    const stars = '★'.repeat(Math.round(ratingsNum)) + '☆'.repeat(5 - Math.round(ratingsNum));
    return '<div class="card-rating"><span class="star">' + stars + '</span>' + ratingsNum.toFixed(1) + '</div>';
  }
  return '<span class="rating-na">Not Rated</span>';
}

function buildReviewTag(review) {
  if (!review) return '';
  const r = review.toLowerCase();
  if (r.includes('excellent'))  return '<span class="review-tag review-excellent">Excellent</span>';
  if (r.includes('very good'))  return '<span class="review-tag review-good">Very Good</span>';
  if (r.includes('average') || r.includes('decent')) return '<span class="review-tag review-average">Average</span>';
  if (r.includes('not satisfactory') || r.includes('poor')) return '<span class="review-tag review-poor">Poor</span>';
  return '<span class="review-tag review-na">No Review</span>';
}

function getSiteClass(website) {
  if (!website) return '';
  const w = website.toLowerCase();
  if (w === 'amazon')   return 'site-amazon';
  if (w === 'flipkart') return 'site-flipkart';
  if (w === 'bestbuy')  return 'site-bestbuy';
  return '';
}

// ===== PAGINATION =====
function renderPagination(page, pages, query) {
  const el = document.getElementById('pagination');
  el.innerHTML = '';
  if (pages <= 1) return;
  const addBtn = (label, pg, active, disabled) => {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (active ? ' active' : '');
    btn.textContent = label;
    btn.disabled = !!disabled;
    btn.onclick = () => { currentPage = pg; searchProducts(query, pg); window.scrollTo({top:0,behavior:'smooth'}); };
    el.appendChild(btn);
  };
  addBtn('← Prev', page-1, false, page<=1);
  const start = Math.max(1, page-2), end = Math.min(pages, page+2);
  for (let i = start; i <= end; i++) addBtn(i, i, i===page, false);
  addBtn('Next →', page+1, false, page>=pages);
}

function showSection(section) {
  document.getElementById('heroSection').style.display  = section==='results' ? 'none' : '';
  document.getElementById('mainContent').style.display  = section==='results' ? 'block' : 'none';
}
function showLoading(show) {
  document.getElementById('loadingState').style.display = show ? 'flex' : 'none';
  if (show) document.getElementById('productGrid').innerHTML = '';
}

// ===== COMPARE MODAL =====
async function openCompare(productName) {
  document.getElementById('compareModal').style.display = 'flex';
  document.getElementById('compareContent').innerHTML =
    '<div class="loading-state" style="padding:40px"><div class="spinner"></div><p>Comparing prices…</p></div>';
  try {
    const res  = await fetch('/api/compare?name=' + encodeURIComponent(productName));
    const data = await res.json();
    renderCompare(data);
  } catch { document.getElementById('compareContent').innerHTML = '<p style="color:var(--red)">Failed to load comparison.</p>'; }
}

function renderCompare(data) {
  if (data.error) { document.getElementById('compareContent').innerHTML = '<p style="color:var(--text2)">' + data.error + '</p>'; return; }
  const listings = data.listings || [];
  const savings  = (data.price_range && data.price_range.savings) || 0;
  const best     = data.best_deal;
  const bestVal  = data.best_value;
  let html = '<p style="color:var(--text2);font-size:13px;margin-bottom:16px">Showing listings for <strong style="color:var(--white)">' + escHtml(data.name) + '</strong></p>';
  html += '<div class="compare-grid">';
  listings.forEach(function(l) {
    const isBest = best && l.id === best.id;
    html += '<div class="compare-item ' + (isBest ? 'best' : '') + '">' +
      (isBest ? '<div style="font-size:10px;color:var(--green);font-weight:700;margin-bottom:4px">🏆 BEST DEAL</div>' : '') +
      '<div class="site-name ' + getSiteClass(l.website) + '">' + escHtml(l.website||'N/A') + '</div>' +
      '<div class="c-price">₹' + (l.price||0).toLocaleString('en-IN') + '</div>' +
      '<div class="c-score">AI Score: ' + (l.ai_score != null ? l.ai_score : 'N/A') + '</div>' +
      '<a href="' + (l.product_link||'#') + '" target="_blank" style="display:inline-block;margin-top:10px;font-size:12px;color:var(--accent2);text-decoration:none" onclick="event.stopPropagation()">View →</a>' +
      '</div>';
  });
  html += '</div>';
  if (savings > 0 && best) {
    html += '<div class="best-deal-banner"><span class="bdl">💰 Best deal on ' + escHtml(best.website) + '</span>' +
      '<span class="bdr">Save up to <span class="savings-badge">₹' + savings.toLocaleString('en-IN') + '</span></span></div>';
  }
  if (best && best.deal_explanation) {
    html += '<div class="deal-explanation"><span class="deal-exp-icon">💡</span><span>' + escHtml(best.deal_explanation) + '</span></div>';
  }
  document.getElementById('compareContent').innerHTML = html;
}

// ===== PREDICT MODAL =====
async function openPredict(productName) {
  document.getElementById('predictModal').style.display = 'flex';
  document.getElementById('predictContent').innerHTML =
    '<div class="loading-state" style="padding:40px"><div class="spinner"></div><p>Running AI forecast…</p></div>';
  if (forecastChart) { forecastChart.destroy(); forecastChart = null; }
  try {
    const res  = await fetch('/api/predict?name=' + encodeURIComponent(productName) + '&days=30');
    const data = await res.json();
    renderPredict(data, productName);
  } catch { document.getElementById('predictContent').innerHTML = '<p style="color:var(--red)">Forecast failed.</p>'; }
}

function renderPredict(data, name) {
  const rec       = data.recommendation || 'HOLD';
  const recReason = data.rec_reason || '';
  const dirColor  = data.direction === 'up' ? 'pb-up' : data.direction === 'down' ? 'pb-down' : 'pb-stable';
  const dirIcon   = data.direction === 'up' ? '↑' : data.direction === 'down' ? '↓' : '→';
  const recColors = { 'WAIT': '#f59e0b', 'BUY': '#10b981', 'BUY NOW': '#10b981', 'HOLD': '#6366f1' };
  const recIcons  = { 'WAIT': '⏳', 'BUY': '🛒', 'BUY NOW': '🛒', 'HOLD': '⚖️' };
  const recColor  = recColors[rec] || '#6366f1';
  const recIcon   = recIcons[rec]  || '⚖️';
  const currentPrice = data.current_price || data.current_avg_price || 0;
  const savings      = data.savings_amount || 0;
  const bestDay      = data.best_time_to_buy || 'N/A';
  const confScore    = data.confidence_score != null ? data.confidence_score : 'N/A';
  const pastPrices   = data.past_prices || [];
  const predPrices   = data.predicted_prices || [];
  const useChart     = pastPrices.length > 0 || predPrices.length > 0;

  let html =
    '<div class="predict-header">' +
      '<h4>' + escHtml(name) + '</h4>' +
      '<p>30-day forecast · <span style="color:var(--accent2)">' + escHtml(data.model || 'ML Forecast') + '</span></p>' +
    '</div>' +
    '<div class="predict-summary">' +
      '<div class="predict-box"><div class="pb-label">Current Price</div><div class="pb-val">₹' + currentPrice.toLocaleString('en-IN') + '</div></div>' +
      '<div class="predict-box"><div class="pb-label">Avg Predicted</div><div class="pb-val">₹' + (data.predicted_price||0).toLocaleString('en-IN') + '</div></div>' +
      '<div class="predict-box"><div class="pb-label">Change</div><div class="pb-val ' + dirColor + '">' + dirIcon + ' ' + Math.abs(data.change_pct||data.change_percent||0) + '%</div></div>' +
    '</div>' +
    '<div class="rec-banner" style="border-color:' + recColor + '">' +
      '<div class="rec-icon" style="background:' + recColor + '20;color:' + recColor + '">' + recIcon + '</div>' +
      '<div class="rec-body">' +
        '<div class="rec-label" style="color:' + recColor + '">' + rec + '</div>' +
        '<div class="rec-reason">' + escHtml(recReason) + '</div>' +
      '</div>' +
    '</div>' +
    '<div class="forecast-meta-row">' +
      '<div class="fmr-item"><div class="fmr-label">💰 Potential Savings</div><div class="fmr-val">' + (savings > 0 ? '₹' + savings.toLocaleString('en-IN') : 'N/A') + '</div></div>' +
      '<div class="fmr-item"><div class="fmr-label">📅 Best Time to Buy</div><div class="fmr-val">' + escHtml(bestDay) + '</div></div>' +
      '<div class="fmr-item"><div class="fmr-label">🎯 Confidence</div><div class="fmr-val">' + confScore + (typeof confScore === 'number' ? '%' : '') + '</div></div>' +
    '</div>';

  if (useChart) {
    html += '<div class="forecast-chart-wrap"><div class="trend-chart-title">Price History & 30-Day Forecast</div><canvas id="forecastCanvas" height="200"></canvas>' +
      '<div class="chart-legend"><span class="legend-past">— Past Prices</span><span class="legend-pred">- - Predicted</span></div></div>';
  } else {
    const trend = data.trend || [];
    const maxP  = Math.max.apply(null, trend.map(function(t){return t.price;})) || 1;
    html += '<div class="trend-chart"><div class="trend-chart-title">Price Trend</div><div class="trend-bars">' +
      trend.map(function(t) {
        return '<div class="trend-bar-wrap"><div class="trend-bar" style="height:' + Math.round((t.price/maxP)*70) + 'px"></div><div class="trend-bar-label">M' + t.month + '</div></div>';
      }).join('') + '</div></div>';
  }

  html += '<div style="display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap">' +
    '<span class="confidence-badge conf-' + (data.confidence||'low') + '">Confidence: ' + (data.confidence||'low') + '</span>' +
    '<span style="font-size:12px;color:var(--text3)">⚠️ Estimates only. Not financial advice.</span>' +
    '</div>';

  document.getElementById('predictContent').innerHTML = html;

  if (useChart) {
    setTimeout(function() { drawForecastChart(pastPrices, predPrices); }, 80);
  }
}

function drawForecastChart(pastPrices, predPrices) {
  const canvas = document.getElementById('forecastCanvas');
  if (!canvas || typeof Chart === 'undefined') return;
  if (forecastChart) { forecastChart.destroy(); forecastChart = null; }

  const pastLabels = pastPrices.map(function(d){ return d.date.slice(5); });
  const pastVals   = pastPrices.map(function(d){ return d.price; });
  const predLabels = predPrices.map(function(d){ return d.date.slice(5); });
  const predVals   = predPrices.map(function(d){ return d.price; });

  // Bridge: last past point + all pred
  const bridge     = pastVals.length ? [pastVals[pastVals.length-1]].concat(predVals) : predVals;
  const bridgeLbl  = pastVals.length ? [pastLabels[pastLabels.length-1]].concat(predLabels) : predLabels;
  const allLabels  = pastLabels.concat(predLabels.slice(pastLabels.length ? 0 : 0));
  // Use separate datasets on a unified axis
  const totalLabels = pastLabels.concat(predLabels);
  const pastFull    = pastVals.concat(new Array(predLabels.length).fill(null));
  const predFull    = new Array(pastLabels.length > 0 ? pastLabels.length - 1 : 0).fill(null).concat(
    pastLabels.length > 0 ? [pastVals[pastVals.length-1]] : []
  ).concat(predVals);

  const skip = Math.max(1, Math.floor(totalLabels.length / 8));
  const tickLabels = totalLabels.map(function(l, i){ return i % skip === 0 ? l : ''; });

  forecastChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: tickLabels,
      datasets: [
        { label: 'Past Price', data: pastFull, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.08)', borderWidth: 2, pointRadius: 0, tension: 0.35, fill: true, spanGaps: false },
        { label: 'Predicted',  data: predFull, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.06)', borderWidth: 2, borderDash: [6,4], pointRadius: 0, tension: 0.35, fill: true, spanGaps: false }
      ]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1,
          titleColor: '#94a3b8', bodyColor: '#f1f5f9',
          callbacks: { label: function(ctx){ return ctx.raw != null ? '₹' + Math.round(ctx.raw).toLocaleString('en-IN') : ''; } }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(148,163,184,0.07)' }, ticks: { color: '#64748b', maxRotation: 0 } },
        y: { grid: { color: 'rgba(148,163,184,0.07)' }, ticks: { color: '#64748b', callback: function(v){ return '₹' + Math.round(v).toLocaleString('en-IN'); } } }
      }
    }
  });
}

// ===== MODAL CLOSE =====
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
  if (id === 'predictModal' && forecastChart) { forecastChart.destroy(); forecastChart = null; }
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { closeModal('compareModal'); closeModal('predictModal'); }
});

// ===== UTILS =====
function escHtml(str) {
  if (str == null) return 'N/A';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  if (str == null) return '';
  return String(str).replace(/'/g,"\\'").replace(/"/g,'&quot;');
}
