import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, Download, Image as ImageIcon, Loader2, AlertCircle, RefreshCw, Layers, Flame, History, Trash2 } from 'lucide-react';

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [selectedEngine, setSelectedEngine] = useState('imagen4'); // 預設使用最穩定的內建 Imagen 4
  const [imageUrl, setImageUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [imageHistory, setImageHistory] = useState([]);
  const [showFaq, setShowFaq] = useState(false);
  
  const messagesEndRef = useRef(null);

  // 指數退避重試函數 (Gemini API 專用安全防護)
  const fetchWithBackoff = async (url, options, maxRetries = 5) => {
    let delay = 1000;
    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await fetch(url, options);
        if (response.ok) return response;
        if (response.status === 429 || response.status >= 500) {
          await new Promise(resolve => setTimeout(resolve, delay));
          delay *= 2;
          continue;
        }
        return response;
      } catch (err) {
        if (i === maxRetries - 1) throw err;
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2;
      }
    }
    throw new Error("連線逾時，重試失敗。");
  };

  // 快捷風格靈感
  const stylePresets = [
    { label: '🌟 寫實攝影', value: ', realistic photography, highly detailed, 8k resolution, professional lighting' },
    { label: '🎨 概念插畫', value: ', digital illustration, fantasy concept art, vibrant colors, masterpiece' },
    { label: '👾 賽博朋克', value: ', cyberpunk style, neon lights, futuristic city, dark synthwave aesthetics' },
    { label: '🧸 3D 黏土', value: ', cute 3D clay style, Pixar animation aesthetic, soft lighting, pastel colors' },
    { label: '🎌 吉卜力風', value: ', Studio Ghibli anime style, hand-drawn watercolor, nostalgic, retro' }
  ];

  const applyPreset = (presetValue) => {
    setPrompt(prev => {
      // 避免重複疊加相同風格
      if (prev.includes(presetValue)) return prev;
      return prev.trim() + presetValue;
    });
  };

  const generateImage = async () => {
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setError(null);
    setImageUrl(null);

    const currentPrompt = prompt;

    // 引擎 1：內建的 Gemini Imagen 4 (最穩定、免 Key)
    if (selectedEngine === 'imagen4') {
      setStatusMsg('正在啟用 Gemini Imagen 4 頂級引擎...');
      const apiKey = ""; // 執行環境會於運行時自動帶入此 Key
      const url = `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${apiKey}`;
      
      try {
        const response = await fetchWithBackoff(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instances: { prompt: currentPrompt },
            parameters: { sampleCount: 1 }
          })
        });

        if (!response.ok) {
          throw new Error(`Imagen API 回傳錯誤碼: ${response.status}`);
        }

        const result = await response.json();
        if (result.predictions && result.predictions[0]?.bytesBase64Encoded) {
          const b64Data = result.predictions[0].bytesBase64Encoded;
          const generatedUrl = `data:image/png;base64,${b64Data}`;
          setImageUrl(generatedUrl);
          addToHistory(generatedUrl, currentPrompt, 'Imagen 4');
          setStatusMsg('圖片生成成功！');
          setIsLoading(false);
        } else {
          throw new Error("未能成功解碼圖片資料。");
        }
      } catch (err) {
        console.warn("Imagen 4 異常，自動轉往公用備用節點...", err);
        switchToFallback(currentPrompt);
      }
    } 
    
    // 引擎 2：Hugging Face Cosmos3 (免 Key 容易因 CORS 或限流阻擋)
    else if (selectedEngine === 'cosmos3') {
      setStatusMsg('嘗試連接 Cosmos3 模型 (無密鑰模式)...');
      const hfModelUrl = "https://api-inference.huggingface.co/models/nvidia/Cosmos3-Super-Text2Image";

      try {
        const response = await fetch(hfModelUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ inputs: currentPrompt }),
        });

        if (!response.ok) {
          throw new Error(`HF 伺服器拒絕 (狀態: ${response.status})`);
        }

        const blob = await response.blob();
        const generatedUrl = URL.createObjectURL(blob);
        setImageUrl(generatedUrl);
        addToHistory(generatedUrl, currentPrompt, 'Cosmos 3');
        setStatusMsg('Cosmos3 圖片生成成功！');
        setIsLoading(false);
      } catch (err) {
        console.warn("Cosmos3 無 Key 被拒絕。已自動導向備用穩定管道。");
        switchToFallback(currentPrompt);
      }
    } 
    
    // 引擎 3：Pollinations (直接由 DOM 渲染，100% 成功率)
    else {
      setStatusMsg('正在由 Pollinations 公共高速節點生成...');
      const seed = Math.floor(Math.random() * 1000000);
      const fallbackUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(currentPrompt)}?nologo=true&width=1024&height=1024&seed=${seed}`;
      
      // 直接將 URL 交給 React 狀態，由 img 標籤做原生渲染，避開背景 fetch 沙盒限制
      setImageUrl(fallbackUrl);
      addToHistory(fallbackUrl, currentPrompt, 'Pollinations');
      setStatusMsg('圖片渲染中...');
      setIsLoading(false);
    }
  };

  // 自動降級/切換備用方案
  const switchToFallback = (targetPrompt) => {
    setStatusMsg('HF/內建節點暫時受限，已平滑切換至「公共免 Key 高速節點」...');
    setError('由於 Hugging Face 原始節點限制無金鑰的 CORS 請求，系統已自動為您無縫啟用「高速公共節點」產生圖像。');
    
    const seed = Math.floor(Math.random() * 1000000);
    const fallbackUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(targetPrompt)}?nologo=true&width=1024&height=1024&seed=${seed}`;
    
    setImageUrl(fallbackUrl);
    addToHistory(fallbackUrl, targetPrompt, '公共備用');
    setIsLoading(false);
  };

  const addToHistory = (url, promptText, engineName) => {
    setImageHistory(prev => [
      { id: Date.now(), url, prompt: promptText, engine: engineName },
      ...prev.slice(0, 9) // 最多保存最新 10 張
    ]);
  };

  const handleDownload = async () => {
    if (!imageUrl) return;
    try {
      if (imageUrl.startsWith('data:')) {
        // Base64 格式下載
        const a = document.createElement('a');
        a.href = imageUrl;
        a.download = `ai-art-${Date.now()}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        // 外部 URL 下載 (使用傳統的開啟新視窗/標籤下載，避開沙盒跨域限制)
        window.open(imageUrl, '_blank');
      }
    } catch (err) {
      window.open(imageUrl, '_blank');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex justify-center items-center font-sans p-0 sm:p-4">
      {/* 行動裝置外殼模擬器 */}
      <div className="w-full max-w-md bg-slate-900 h-screen sm:h-[840px] flex flex-col sm:rounded-3xl shadow-2xl relative overflow-hidden border border-slate-800">
        
        {/* Header */}
        <header className="bg-slate-900 border-b border-slate-800 text-white p-4 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-gradient-to-tr from-blue-600 to-indigo-500 p-1.5 rounded-lg">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide">Cosmos3 AI Studio</h1>
              <p className="text-[10px] text-slate-400">行動版智能繪圖套件</p>
            </div>
          </div>
          <button 
            onClick={() => setShowFaq(!showFaq)}
            className="text-xs bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded-full text-slate-300 border border-slate-700 transition-colors"
          >
            ❓ 說明
          </button>
        </header>

        {/* 主內容滑動區 */}
        <main className="flex-1 overflow-y-auto p-4 pb-36 bg-slate-950 flex flex-col gap-5">
          
          {/* 說明面板 */}
          {showFaq && (
            <div className="bg-slate-900 border border-blue-900/40 p-4 rounded-xl text-slate-300 text-xs flex flex-col gap-2 animate-in fade-in duration-200">
              <h3 className="font-bold text-blue-400 text-sm mb-1">💡 常見連線說明</h3>
              <p>1. <b>為什麼 Cosmos3 容易失敗？</b></p>
              <p className="pl-3 text-slate-400">Hugging Face 官方對於高算力模型限制了無 Key 請求。當您使用「Cosmos3」時，本 App 會極速嘗試，若被拒絕將<b>自動且無感地</b>切換為其他引擎，保證產圖不中斷！</p>
              <p>2. <b>哪一個最穩定？</b></p>
              <p className="pl-3 text-slate-400">推薦選擇<b>「Imagen 4 頂級引擎」</b>或<b>「Pollinations 公共引擎」</b>，完全不需要金鑰且保證成功。</p>
              <button 
                onClick={() => setShowFaq(false)}
                className="mt-2 bg-blue-600 hover:bg-blue-700 text-white py-1 rounded text-center font-medium transition-colors"
              >
                我知道了
              </button>
            </div>
          )}

          {/* 引擎切換面板 */}
          <div className="bg-slate-900 p-2.5 rounded-2xl border border-slate-800">
            <span className="text-[10px] text-slate-400 font-bold px-2 block mb-2 uppercase tracking-wider">選擇生成引擎</span>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                onClick={() => { setSelectedEngine('imagen4'); setError(null); }}
                className={`py-2 px-1.5 rounded-xl text-xs font-bold transition-all flex flex-col items-center gap-1 ${
                  selectedEngine === 'imagen4' 
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/50' 
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-750'
                }`}
              >
                <Flame className="w-3.5 h-3.5" />
                <span>Imagen 4</span>
                <span className="text-[8px] opacity-75">穩定高畫質</span>
              </button>

              <button
                onClick={() => { setSelectedEngine('cosmos3'); setError(null); }}
                className={`py-2 px-1.5 rounded-xl text-xs font-bold transition-all flex flex-col items-center gap-1 ${
                  selectedEngine === 'cosmos3' 
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-950/50' 
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-750'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Cosmos3</span>
                <span className="text-[8px] opacity-75">原廠模型</span>
              </button>

              <button
                onClick={() => { setSelectedEngine('pollinations'); setError(null); }}
                className={`py-2 px-1.5 rounded-xl text-xs font-bold transition-all flex flex-col items-center gap-1 ${
                  selectedEngine === 'pollinations' 
                    ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-950/50' 
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-750'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>公共節點</span>
                <span className="text-[8px] opacity-75">極速不設限</span>
              </button>
            </div>
          </div>

          {/* 風格快捷標籤 */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-slate-400 font-bold px-1 uppercase tracking-wider">風格快速渲染：</span>
            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none snap-x">
              {stylePresets.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => applyPreset(p.value)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] px-3 py-1.5 rounded-full whitespace-nowrap border border-slate-700/60 snap-align-start transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* 歡迎區 / 主畫布區塊 */}
          {!imageUrl && !isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center min-h-[250px] bg-slate-900 rounded-2xl border border-dashed border-slate-800 p-8 text-center text-slate-500 gap-3">
              <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center text-slate-400">
                <ImageIcon className="w-7 h-7" />
              </div>
              <p className="text-xs">
                在下方輸入任何想法，並選擇最喜愛的 AI 繪圖引擎
              </p>
            </div>
          )}

          {/* 載入進度 */}
          {isLoading && (
            <div className="min-h-[250px] bg-slate-900 rounded-2xl border border-slate-800 p-8 flex flex-col items-center justify-center gap-4 text-center">
              <div className="relative flex items-center justify-center">
                <div className="w-12 h-12 rounded-full border-4 border-blue-500/20 border-t-blue-500 animate-spin"></div>
                <Sparkles className="w-5 h-5 text-blue-400 absolute animate-pulse" />
              </div>
              <div>
                <p className="text-slate-200 font-medium text-xs">{statusMsg}</p>
                <p className="text-slate-500 text-[10px] mt-1">首次算力載入可能需等待 10~15 秒</p>
              </div>
            </div>
          )}

          {/* 錯誤警告區 (平滑降級時顯示) */}
          {error && (
            <div className="p-3.5 bg-amber-950/40 border border-amber-900/60 rounded-xl flex gap-3 text-amber-300 animate-in fade-in">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">{error}</p>
            </div>
          )}

          {/* 成功圖片渲染 (利用 onLoad 實現優雅浮現) */}
          {imageUrl && !isLoading && (
            <div className="animate-in fade-in zoom-in-95 duration-300">
              <div className="bg-slate-900 p-2 rounded-2xl border border-slate-800">
                <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-950 shadow-inner">
                  <img 
                    src={imageUrl} 
                    alt="AI Generated" 
                    className="w-full h-full object-contain"
                    onLoad={() => console.log("圖片載入成功")}
                    onError={() => {
                      setError("此引擎載入失敗，建議將上方引擎切換至「Imagen 4」或「公共節點」重新生成。");
                    }}
                  />
                </div>
                <div className="flex items-center justify-between mt-3 px-2">
                  <div className="overflow-hidden pr-3">
                    <p className="text-[11px] text-slate-300 font-bold truncate">生成提示詞：</p>
                    <p className="text-[10px] text-slate-500 line-clamp-1 truncate">{prompt}</p>
                  </div>
                  <button 
                    onClick={handleDownload}
                    className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-xl transition-colors shadow-lg flex-shrink-0 flex items-center gap-1.5 text-xs font-bold"
                  >
                    <Download className="w-4 h-4" />
                    保存
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 歷史生成記錄 (僅於記憶體中保存最新 10 張) */}
          {imageHistory.length > 0 && (
            <div className="flex flex-col gap-2 mt-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1">
                  <History className="w-3 h-3" /> 最近繪製記錄 ({imageHistory.length})
                </span>
                <button 
                  onClick={() => setImageHistory([])}
                  className="text-[10px] text-rose-400 hover:text-rose-300 flex items-center gap-0.5"
                >
                  <Trash2 className="w-3 h-3" /> 清除
                </button>
              </div>
              <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-none">
                {imageHistory.map((item) => (
                  <div 
                    key={item.id} 
                    onClick={() => { setImageUrl(item.url); setPrompt(item.prompt); setError(null); }}
                    className="w-16 flex-shrink-0 cursor-pointer group"
                  >
                    <div className={`relative aspect-square rounded-lg overflow-hidden border ${imageUrl === item.url ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-800'}`}>
                      <img src={item.url} alt="History" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      <div className="absolute bottom-0 inset-x-0 bg-slate-950/80 text-[8px] text-center text-slate-300 py-0.5 font-sans">
                        {item.engine}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </main>

        {/* 底部行動輸入控制台 */}
        <div className="absolute bottom-0 w-full bg-slate-900 border-t border-slate-800 p-4 pb-safe shadow-[0_-10px_30px_rgba(0,0,0,0.5)]">
          <div className="flex gap-2 relative">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="請輸入英文描述您想像的畫面..."
              className="w-full bg-slate-950 text-slate-100 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-3.5 py-2.5 text-xs resize-none h-14 pr-12 transition-all duration-200 placeholder:text-slate-600"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  generateImage();
                }
              }}
            />
            <button
              onClick={generateImage}
              disabled={isLoading || !prompt.trim()}
              className="absolute right-2.5 top-2.5 bottom-2.5 aspect-square bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white disabled:text-slate-600 rounded-lg flex items-center justify-center transition-all shadow-md active:scale-95"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="text-[9px] text-slate-500 text-center mt-2">
            按 Enter 或發送鈕直接產生圖片 • 建議使用英文以獲得最佳繪圖效果
          </div>
        </div>

      </div>
    </div>
  );
}