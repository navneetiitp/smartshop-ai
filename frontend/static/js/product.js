// product.js — runs on /product/<id>
let forecastChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  const main = document.getElementById('detailMain');
  try {
    const res = await fetch('/api/product/' + productId);
    if (!res.ok) throw new Error('Not found');
    const p = await res.json();
    const sumRes = await fetch('/api/summary/' + productId);
    const sumData = await sumRes.json();
    const cmpRes = await fetch('/api/compare?name=' + encodeURIComponent(p.product_name));
    const cmpData = await cmpRes.json();
    renderDetail(main, p, sumData, cmpData);
  } catch (err) {
    main.innerHTML = '<div class="detail-loading"><p style="color:var(--red)">Failed to load product. <a href="/" style="color:var(--accent2)">Go back</a></p></div>';
  }
});

function renderDetail(container, p, sumData, cmpData) {
  const siteBadgeClass = getSiteClass(p.website);
  const ratingHtml     = buildRatingHtml(p.ratings_num, p.ratings);
  const reviewTag      = buildReviewTag(p.reviews);
  const score          = p.ai_score || 0;
  const specs          = parseSpecs(p.product_description);
  const summary        = (sumData && sumData.summary) || '';
  const listings       = ((cmpData && cmpData.listings) || []).filter(function(l){ return l.id !== p.id; });
  const best           = (cmpData && cmpData.best_deal) || null;
  const bestValue      = (cmpData && cmpData.best_value) || null;

  let specsHtml = '';
  for (const [key, val] of Object.entries(specs)) {
    specsHtml += '<div class="spec-row"><div class="spec-key">' + escHtml(key) + '</div><div class="spec-val">' + escHtml(val) + '</div></div>';
  }
  if (!specsHtml) specsHtml = '<div class="spec-row"><div class="spec-val" style="color:var(--text3)">' + escHtml(p.product_description) + '</div></div>';

  let listingsHtml = '';
  if (listings.length > 0) {
    listingsHtml = '<div class="other-listings"><h3>Available on Other Stores</h3><div class="listings-table">';
    listings.sort(function(a,b){return a.price-b.price;}).forEach(function(l) {
      const isBest = best && l.id === best.id;
      var badgeHtml = '';
      if (l.badge === 'both') badgeHtml = '<span class="badge-combined">🏆 Best Deal &amp; Value</span>';
      else if (l.badge === 'best_deal') badgeHtml = '<span class="badge-deal">💰 Best Deal</span>';
      else if (l.badge === 'best_value') badgeHtml = '<span class="badge-value">⭐ Best Value</span>';
      listingsHtml += '<div class="listing-row' + (l.badge ? ' listing-highlighted' : '') + '">' +
        '<div class="lr-site ' + getSiteClass(l.website) + '">' + escHtml(l.website||'N/A') + '</div>' +
        (badgeHtml ? '<div class="lr-badge">' + badgeHtml + '</div>' : '') +
        '<div class="lr-price">₹' + (l.price||0).toLocaleString('en-IN') + '</div>' +
        '<div class="lr-score">AI: ' + (l.ai_score != null ? l.ai_score : 'N/A') + '</div>' +
        '<a href="' + (l.product_link||'#') + '" target="_blank" class="lr-btn">Buy Here →</a>' +
        '</div>';
    });
    listingsHtml += '</div></div>';
  }

  // Best deal explanation on detail page
  let bestDealHtml = '';
  if (best && best.deal_explanation) {
    bestDealHtml += '<div class="deal-explanation" style="margin-top:8px"><span class="deal-exp-icon">💰</span><span>' + escHtml(best.deal_explanation) + '</span></div>';
  }
  if (bestValue && bestValue.value_explanation && (!best || bestValue.id !== best.id)) {
    bestDealHtml += '<div class="deal-explanation" style="margin-top:8px"><span class="deal-exp-icon">⭐</span><span>' + escHtml(bestValue.value_explanation) + '</span></div>';
  } else if (bestValue && bestValue.value_explanation && best && bestValue.id === best.id) {
    bestDealHtml += '<div class="deal-explanation" style="margin-top:8px"><span class="deal-exp-icon">⭐</span><span>' + escHtml(bestValue.value_explanation) + '</span></div>';
  }

  const predictSection =
    '<div style="margin-top:40px;background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">' +
      '<div>' +
        '<div style="font-size:16px;font-weight:700;color:var(--white);margin-bottom:4px">📈 Price Forecast</div>' +
        '<div style="font-size:13px;color:var(--text2)">See where this price is headed in the next 30 days</div>' +
      '</div>' +
      '<button class="btn-secondary" onclick="openPredictDetail(\'' + escAttr(p.product_name) + '\')">Run AI Forecast</button>' +
    '</div>';

  container.innerHTML =
    '<div class="detail-grid">' +
      '<div class="detail-info">' +
        '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">' +
          '<span class="card-site-badge ' + siteBadgeClass + '">' + escHtml(p.website||'N/A') + '</span>' +
          reviewTag +
        '</div>' +
        '<h1 class="detail-name">' + escHtml(p.product_name||'N/A') + '</h1>' +
        '<div class="detail-price-big"><span class="currency">₹</span>' + (p.price||0).toLocaleString('en-IN') + '</div>' +
        (ratingHtml ? '<div style="font-size:14px">' + ratingHtml + '</div>' : '') +
        '<div class="detail-ai-score">' +
          '<div class="score-row"><span class="score-label">⚡ AI Score</span><span class="score-val">' + score + ' / 100</span></div>' +
          '<div class="detail-score-bar"><div class="detail-score-fill" style="width:' + score + '%"></div></div>' +
          '<p style="font-size:12px;color:var(--text3);margin-top:8px">Based on price competitiveness, rating, review sentiment & recency</p>' +
        '</div>' +
        (summary ? '<div class="detail-summary-box"><h4>🤖 AI Summary</h4><p>' + renderMarkdown(summary) + '</p></div>' : '') +
        bestDealHtml +
        '<div class="detail-actions">' +
          '<a href="' + (p.product_link||'#') + '" target="_blank" class="btn-primary">Buy on ' + escHtml(p.website||'Store') + ' →</a>' +
          '<button class="btn-secondary" onclick="openCompareDetail(\'' + escAttr(p.product_name) + '\')">Compare Prices</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div style="margin-top:40px"><h3 style="font-size:18px;font-weight:700;color:var(--white);margin-bottom:16px">📋 Specifications</h3><div class="detail-specs">' + specsHtml + '</div></div>' +
    listingsHtml +
    predictSection;
}

// ===== MODALS =====
async function openCompareDetail(name) {
  const modal = showModal('Price Comparison');
  try {
    const res  = await fetch('/api/compare?name=' + encodeURIComponent(name));
    const data = await res.json();
    modal.querySelector('.modal-body').innerHTML = renderCompareHtml(data);
  } catch {
    modal.querySelector('.modal-body').innerHTML = '<p style="color:var(--red)">Failed to load comparison.</p>';
  }
}

async function openPredictDetail(name) {
  if (forecastChart) { forecastChart.destroy(); forecastChart = null; }
  const modal = showModal('Price Forecast');
  try {
    const res  = await fetch('/api/predict?name=' + encodeURIComponent(name) + '&days=30');
    const data = await res.json();
    modal.querySelector('.modal-body').innerHTML = renderPredictHtml(data, name);
    const pastPrices = data.past_prices || [];
    const predPrices = data.predicted_prices || [];
    if (pastPrices.length > 0 || predPrices.length > 0) {
      setTimeout(function(){ drawForecastChart(pastPrices, predPrices); }, 80);
    }
  } catch {
    modal.querySelector('.modal-body').innerHTML = '<p style="color:var(--red)">Forecast failed.</p>';
  }
}

function showModal(title) {
  const existing = document.getElementById('dynamicModal');
  if (existing) existing.remove();
  const modal = document.createElement('div');
  modal.id = 'dynamicModal';
  modal.className = 'modal';
  modal.style.display = 'flex';
  modal.innerHTML =
    '<div class="modal-backdrop" onclick="this.parentElement.remove()"></div>' +
    '<div class="modal-box">' +
      '<div class="modal-header"><h3>' + title + '</h3>' +
        '<button class="modal-close" onclick="document.getElementById(\'dynamicModal\').remove()">✕</button>' +
      '</div>' +
      '<div class="modal-body"><div class="loading-state" style="padding:40px"><div class="spinner"></div><p>Loading…</p></div></div>' +
    '</div>';
  document.body.appendChild(modal);
  return modal;
}

function renderCompareHtml(data) {
  if (data.error) return '<p style="color:var(--text2)">' + data.error + '</p>';
  const listings = data.listings || [];
  const best     = data.best_deal;
  const bestVal  = data.best_value;
  const savings  = (data.price_range && data.price_range.savings) || 0;
  let html = '<div class="compare-grid">';
  listings.forEach(function(l) {
    const isBest = best && l.id === best.id;
    var isBestVal  = bestVal && l.id === bestVal.id;
    var badge = l.badge;
    var badgeEl = '';
    if (badge === 'both')       badgeEl = '<div class="compare-badge badge-combined">🏆 Best Deal &amp; Value</div>';
    else if (badge === 'best_deal')  badgeEl = '<div class="compare-badge badge-deal">💰 Best Deal</div>';
    else if (badge === 'best_value') badgeEl = '<div class="compare-badge badge-value">⭐ Best Value</div>';
    html += '<div class="compare-item ' + (isBest || isBestVal ? 'best' : '') + '">' +
      badgeEl +
      '<div class="site-name ' + getSiteClass(l.website) + '">' + escHtml(l.website||'N/A') + '</div>' +
      '<div class="c-price">₹' + (l.price||0).toLocaleString('en-IN') + '</div>' +
      '<div class="c-score">AI Score: ' + (l.ai_score != null ? l.ai_score : 'N/A') + '</div>' +
      '<a href="' + (l.product_link||'#') + '" target="_blank" style="display:inline-block;margin-top:10px;font-size:12px;color:var(--accent2);text-decoration:none">View →</a>' +
      '</div>';
  });
  html += '</div>';
  if (savings > 0 && best) {
    html += '<div class="best-deal-banner"><span class="bdl">💰 Best deal on ' + escHtml(best.website) + '</span>' +
      '<span class="bdr">Save up to <span class="savings-badge">₹' + savings.toLocaleString('en-IN') + '</span></span></div>';
  }
  if (best && best.deal_explanation) {
    html += '<div class="deal-explanation"><span class="deal-exp-icon">💰</span><span>' + escHtml(best.deal_explanation) + '</span></div>';
  }
  if (bestVal && bestVal.value_explanation) {
    html += '<div class="deal-explanation"><span class="deal-exp-icon">⭐</span><span>' + escHtml(bestVal.value_explanation) + '</span></div>';
  }
  return html;
}

function renderPredictHtml(data, name) {
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
  const hasPast = (data.past_prices || []).length > 0;
  const hasPred = (data.predicted_prices || []).length > 0;
  const useChart = hasPast || hasPred;

  let html =
    '<div class="predict-header"><h4>' + escHtml(name) + '</h4><p>30-day forecast · <span style="color:var(--accent2)">' + escHtml(data.model || 'ML Forecast') + '</span></p></div>' +
    '<div class="predict-summary">' +
      '<div class="predict-box"><div class="pb-label">Current Price</div><div class="pb-val">₹' + currentPrice.toLocaleString('en-IN') + '</div></div>' +
      '<div class="predict-box"><div class="pb-label">Avg Predicted</div><div class="pb-val">₹' + (data.predicted_price||0).toLocaleString('en-IN') + '</div></div>' +
      '<div class="predict-box"><div class="pb-label">Change</div><div class="pb-val ' + dirColor + '">' + dirIcon + ' ' + Math.abs(data.change_pct||data.change_percent||0) + '%</div></div>' +
    '</div>' +
    '<div class="rec-banner" style="border-color:' + recColor + '">' +
      '<div class="rec-icon" style="background:' + recColor + '20;color:' + recColor + '">' + recIcon + '</div>' +
      '<div class="rec-body"><div class="rec-label" style="color:' + recColor + '">' + rec + '</div><div class="rec-reason">' + escHtml(recReason) + '</div></div>' +
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
    const maxP  = Math.max.apply(null, trend.map(function(t){ return t.price; })) || 1;
    html += '<div class="trend-chart"><div class="trend-chart-title">Price Trend</div><div class="trend-bars">' +
      trend.map(function(t){ return '<div class="trend-bar-wrap"><div class="trend-bar" style="height:' + Math.round((t.price/maxP)*70) + 'px"></div><div class="trend-bar-label">M' + t.month + '</div></div>'; }).join('') +
      '</div></div>';
  }
  html += '<div style="display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap">' +
    '<span class="confidence-badge conf-' + (data.confidence||'low') + '">Confidence: ' + (data.confidence||'low') + '</span>' +
    '<span style="font-size:12px;color:var(--text3)">⚠️ Estimates only. Not financial advice.</span></div>';
  return html;
}

function drawForecastChart(pastPrices, predPrices) {
  const canvas = document.getElementById('forecastCanvas');
  if (!canvas || typeof Chart === 'undefined') return;
  if (forecastChart) { forecastChart.destroy(); forecastChart = null; }
  const pastLabels = pastPrices.map(function(d){ return d.date.slice(5); });
  const pastVals   = pastPrices.map(function(d){ return d.price; });
  const predLabels = predPrices.map(function(d){ return d.date.slice(5); });
  const predVals   = predPrices.map(function(d){ return d.price; });
  const totalLabels = pastLabels.concat(predLabels);
  const pastFull    = pastVals.concat(new Array(predLabels.length).fill(null));
  const bridge      = pastVals.length ? [pastVals[pastVals.length-1]] : [];
  const predFull    = new Array(Math.max(0, pastLabels.length-1)).fill(null).concat(bridge).concat(predVals);
  const skip        = Math.max(1, Math.floor(totalLabels.length/8));
  const tickLabels  = totalLabels.map(function(l,i){ return i%skip===0 ? l : ''; });
  forecastChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: tickLabels,
      datasets: [
        { label:'Past Price', data: pastFull, borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,0.08)', borderWidth:2, pointRadius:0, tension:0.35, fill:true, spanGaps:false },
        { label:'Predicted',  data: predFull, borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.06)', borderWidth:2, borderDash:[6,4], pointRadius:0, tension:0.35, fill:true, spanGaps:false }
      ]
    },
    options: {
      responsive:true,
      interaction:{ mode:'index', intersect:false },
      plugins:{
        legend:{ display:false },
        tooltip:{ backgroundColor:'#1e293b', borderColor:'#334155', borderWidth:1, titleColor:'#94a3b8', bodyColor:'#f1f5f9',
          callbacks:{ label:function(ctx){ return ctx.raw!=null ? '₹'+Math.round(ctx.raw).toLocaleString('en-IN') : ''; } } }
      },
      scales:{
        x:{ grid:{color:'rgba(148,163,184,0.07)'}, ticks:{color:'#64748b',maxRotation:0} },
        y:{ grid:{color:'rgba(148,163,184,0.07)'}, ticks:{color:'#64748b', callback:function(v){ return '₹'+Math.round(v).toLocaleString('en-IN'); }} }
      }
    }
  });
}

// ===== UTILS =====
function parseSpecs(desc) {
  if (!desc) return {};
  const specs = {};
  const patterns = [['Processor',/Processor:\s*([^,]+)/i],['RAM',/RAM:\s*([^,]+)/i],['Storage',/Storage:\s*([^,]+)/i],['Operating System',/OS:\s*([^,]+)/i],['Display',/Display:\s*([^,]+)/i]];
  for (const [label, re] of patterns) { const m = desc.match(re); if (m) specs[label] = m[1].trim(); }
  return specs;
}
function buildRatingHtml(ratingsNum, ratingsRaw) {
  if (ratingsNum && ratingsNum > 0) {
    const stars = '★'.repeat(Math.round(ratingsNum)) + '☆'.repeat(5-Math.round(ratingsNum));
    return '<div class="card-rating"><span class="star">' + stars + '</span> ' + ratingsNum.toFixed(1) + ' / 5</div>';
  }
  return '<span class="rating-na">Not Rated</span>';
}
function buildReviewTag(review) {
  if (!review) return '';
  const r = review.toLowerCase();
  if (r.includes('excellent'))  return '<span class="review-tag review-excellent">Excellent</span>';
  if (r.includes('very good'))  return '<span class="review-tag review-good">Very Good</span>';
  if (r.includes('average') || r.includes('decent')) return '<span class="review-tag review-average">Average</span>';
  if (r.includes('not satisfactory')) return '<span class="review-tag review-poor">Poor</span>';
  return '<span class="review-tag review-na">No Review</span>';
}
function getSiteClass(website) {
  if (!website) return '';
  const w = website.toLowerCase();
  if (w==='amazon') return 'site-amazon'; if (w==='flipkart') return 'site-flipkart'; if (w==='bestbuy') return 'site-bestbuy';
  return '';
}
function renderMarkdown(text) { return text.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>'); }
function escHtml(str) { if (str==null) return 'N/A'; return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(str) { if (str==null) return ''; return String(str).replace(/'/g,"\\'").replace(/"/g,'&quot;'); }
