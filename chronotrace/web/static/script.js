
document.addEventListener('DOMContentLoaded', () => {
    // ==========================================
    // State Management
    // ==========================================
    const state = {
        traceData: [],
        sourceLines: [],
        capturedOutput: [],
        startLine: 0,
        currentStep: 0,
        isPlaying: false,
        playSpeed: 100, // ms
        autoScroll: true,
        playInterval: null,
        breakpoints: new Set(), // Line numbers with breakpoints
        breakpointMode: false, // Breakpoint toggle mode
        skipToBreakpoint: false // Skip to next breakpoint
    };

    // DOM Elements Cache (optimized)
    const dom = {
        codeDisplay: document.getElementById('code-display'),
        timelineSlider: document.getElementById('timeline-slider'),
        timeDisplay: document.getElementById('time-display'),
        variablesContainer: document.getElementById('variables-container'),
        stepInsightBox: document.getElementById('step-insight'),
        insightText: document.getElementById('insight-text'),
        currentStepDisplay: document.getElementById('current-step'),
        totalStepsDisplay: document.getElementById('total-steps'),
        lineHighlight: document.getElementById('line-highlight'),
        currentLineBadge: document.getElementById('current-line-badge'),
        statusText: document.getElementById('status-text'),
        btnPlayPause: document.getElementById('btn-play-pause'),
        lineNumbersContainer: document.getElementById('line-numbers'),
        consoleLastLine: document.getElementById('console-last-line'),
        execTime: document.getElementById('exec-time'),
        lineTime: document.getElementById('line-time'),
        currentMem: document.getElementById('current-mem'),
        peakMem: document.getElementById('peak-mem'),
        callStackContainer: document.getElementById('call-stack-container'),
        breakpointModeBtn: document.getElementById('btn-breakpoint-mode'),
        breakpointCount: document.getElementById('breakpoint-count'),
        codeContainer: document.querySelector('.code-container')
    };

    // Element reference cache for frequently accessed elements
    const elementCache = {};

    // Icons
    const ICONS = {
        PLAY: '<i class="ri-play-fill"></i>',
        PAUSE: '<i class="ri-pause-fill"></i>',
        BREAKPOINT_ON: '<i class="ri-checkbox-blank-circle-fill"></i>',
        BREAKPOINT_OFF: '<i class="ri-checkbox-blank-circle-line"></i>'
    };

    // ==========================================
    // Initialization
    // ==========================================
    function init() {
        // Initialize Settings
        state.playSpeed = localStorage.getItem('huay_speed') || 100;
        state.autoScroll = localStorage.getItem('huay_autoscroll') !== 'false';
        
        // Listen for storage changes (settings sync)
        window.addEventListener('storage', (e) => {
            if (e.key === 'huay_speed') state.playSpeed = parseInt(e.newValue);
            if (e.key === 'huay_autoscroll') state.autoScroll = e.newValue !== 'false';
        });

        fetchTraceData();
        setupEventListeners();
    }

    function fetchTraceData() {
        return fetch('/api/trace')
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (!data || Object.keys(data).length === 0) {
                    showErrorPanel('暂无执行数据', '请先在代码编辑器中运行代码，然后再查看追踪结果。', '/editor', '去写代码');
                    return;
                }
                if (!data.trace || data.trace.length === 0) {
                    showErrorPanel('追踪数据为空', '代码执行完成但未捕获到追踪数据。可能原因：代码执行时间过短或未触发行事件。', '/editor', '重新运行');
                    return;
                }

                // Update State
                state.traceData = data.trace;
                state.sourceLines = data.source;
                state.capturedOutput = data.output || [];
                state.startLine = data.start_line;

                // Initialize UI Components
                renderSourceCode();
                
                // Setup Timeline
                dom.timelineSlider.max = state.traceData.length - 1;
                dom.totalStepsDisplay.textContent = state.traceData.length - 1;

                // Initial Render
                updateState(0);
                
                // Show ready status
                updateStatus('Ready', 'status-val');
            })
            .catch(err => {
                console.error("Error fetching trace:", err);
                let title = '数据加载失败';
                let message = '无法连接到服务器';
                
                if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                    message = '无法连接到后端服务，请确认服务器已启动。';
                } else if (err.message.includes('500')) {
                    message = '服务器内部错误，请检查代码是否有语法错误。';
                } else if (err.message.includes('404')) {
                    message = 'API接口不存在，请检查项目配置。';
                } else {
                    message = `错误详情: ${err.message}`;
                }
                
                showErrorPanel(title, message, '/editor', '返回编辑器');
                updateStatus('Error', 'text-danger');
            });
    }

    function showErrorPanel(title, message, link, linkText, icon) {
        icon = icon || 'ri-information-line';
        const html = 
            '<div class="error-panel">' +
                '<div class="decoration decoration-1"></div>' +
                '<div class="decoration decoration-2"></div>' +
                '<div class="decoration decoration-3"></div>' +
                '<div class="decoration decoration-4"></div>' +
                '<div class="error-icon"><i class="' + icon + '"></i></div>' +
                '<h2 class="error-title">' + title + '</h2>' +
                '<p class="error-message">' + message + '</p>' +
                '<a href="' + link + '" class="error-link">' +
                    '<i class="ri-arrow-right-line"></i>' +
                    '<span>' + linkText + '</span>' +
                '</a>' +
            '</div>';
        dom.codeDisplay.innerHTML = html;
    }

    // ==========================================
    // UI Rendering Logic
    // ==========================================
    function renderSourceCode() {
        if (!state.sourceLines || state.sourceLines.length === 0) {
            dom.codeDisplay.textContent = "源代码不可用。";
            return;
        }
        
        const codeText = state.sourceLines.join('');
        dom.codeDisplay.textContent = codeText;
        Prism.highlightElement(dom.codeDisplay);

        renderLineNumbers();
    }

    function renderLineNumbers() {
        if (!dom.lineNumbersContainer) return;
        
        dom.lineNumbersContainer.innerHTML = '';
        state.sourceLines.forEach((_, index) => {
            const span = document.createElement('span');
            span.textContent = state.startLine + index;
            span.className = 'line-num';
            span.id = `line-num-${state.startLine + index}`;
            dom.lineNumbersContainer.appendChild(span);
        });
    }

    function updateState(stepIndex) {
        stepIndex = parseInt(stepIndex);
        if (isNaN(stepIndex) || stepIndex < 0 || stepIndex >= state.traceData.length) return;
        
        const prevStepIndex = state.currentStep;
        state.currentStep = stepIndex;
        
        // Update Controls
        dom.timelineSlider.value = stepIndex;
        dom.currentStepDisplay.textContent = stepIndex;
        
        const step = state.traceData[stepIndex];
        const prevStep = stepIndex > 0 ? state.traceData[stepIndex - 1] : null;
        
        // Batch DOM updates
        requestAnimationFrame(() => {
            highlightLine(step.line_no);
            renderVariables(step.locals, prevStep ? prevStep.locals : {});
            renderStepInsight(step, prevStep);
            updateConsole(step.timestamp);
            renderCallStack(step.call_stack || []);
            updateStats(step);
            
            if (dom.currentLineBadge) {
                dom.currentLineBadge.textContent = `${step.line_no}`;
            }
            if (dom.timeDisplay) {
                dom.timeDisplay.textContent = new Date(step.timestamp * 1000).toISOString().substr(14, 9);
            }
        });
    }

    function updateStats(step) {
        // Execution time - check if field exists
        if (dom.execTime) {
            if (step && 'elapsed_time' in step && step.elapsed_time !== undefined) {
                dom.execTime.textContent = formatTimeValue(step.elapsed_time);
            } else {
                dom.execTime.textContent = '需重新运行';
            }
        }
        
        // Line execution time
        if (dom.lineTime) {
            if (step && 'exec_time_delta' in step && step.exec_time_delta !== undefined) {
                dom.lineTime.textContent = formatTimeValue(step.exec_time_delta);
            } else {
                dom.lineTime.textContent = '需重新运行';
            }
        }
        
        // Current memory
        if (dom.currentMem) {
            const mem = step?.memory || 0;
            dom.currentMem.textContent = formatBytes(mem);
        }
        
        // Peak memory
        if (dom.peakMem) {
            const peak = step?.peak_memory || 0;
            dom.peakMem.textContent = formatBytes(peak);
        }
    }

    function formatTimeValue(value) {
        // Handle undefined, null, NaN
        if (value === undefined || value === null) return '0.0μs';
        
        const num = Number(value);
        if (isNaN(num)) return '0.0μs';
        
        // Get absolute value for comparison
        const abs = Math.abs(num);
        
        if (abs === 0) return '0.0μs';
        if (abs < 0.000000001) return (num * 1000000000000).toFixed(1) + 'ps';
        if (abs < 0.000001) return (num * 1000000000).toFixed(1) + 'ns';
        if (abs < 0.001) return (num * 1000000).toFixed(1) + 'μs';
        if (abs < 1) return (num * 1000).toFixed(2) + 'ms';
        return num.toFixed(3) + 's';
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }

    function renderCallStack(callStack) {
        if (!dom.callStackContainer) return;
        
        if (!callStack || callStack.length === 0) {
            dom.callStackContainer.innerHTML = '<div class="stack-empty">全局作用域</div>';
            return;
        }

        let html = '';
        callStack.forEach((frame, index) => {
            const isCurrent = index === callStack.length - 1;
            html += `
                <div class="stack-item ${isCurrent ? 'current' : ''}">
                    <i class="ri-function-line" style="color: ${isCurrent ? 'var(--accent-primary)' : 'var(--accent-secondary)'}"></i>
                    <span class="stack-func-name ${isCurrent ? 'current' : ''}">${escapeHtml(frame.name)}</span>
                    <span class="stack-line">L${frame.line}</span>
                </div>
            `;
        });
        
        dom.callStackContainer.innerHTML = html;
        
        // Scroll to bottom to show current function
        dom.callStackContainer.scrollTop = dom.callStackContainer.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function highlightLine(lineNo) {
        const relativeLine = lineNo - state.startLine;
        
        // Reset previous active line
        const prevActive = document.querySelector('.line-num.active');
        if (prevActive) prevActive.classList.remove('active');

        // Highlight current line number
        const currentLineNumEl = document.getElementById(`line-num-${lineNo}`);
        if (currentLineNumEl) currentLineNumEl.classList.add('active');

        if (relativeLine < 0 || relativeLine >= state.sourceLines.length) {
            if (dom.lineHighlight) dom.lineHighlight.style.display = 'none';
            return;
        }
        
        const scrollContainer = document.querySelector('.code-container');
        if (!scrollContainer || !dom.codeDisplay || !dom.lineHighlight) return;

        // Calculate position (Assuming 1.6 line-height and 13px font size => ~20.8px)
        // Better to measure
        const lineHeight = 20.8; 
        const top = (relativeLine * lineHeight);
        
        // Apply styles
        dom.lineHighlight.style.display = 'block';
        dom.lineHighlight.style.top = top + 'px';
        
        // Auto-scroll
        if (state.autoScroll) {
            const containerHeight = scrollContainer.clientHeight;
            const scrollTop = scrollContainer.scrollTop;
            
            if (top < scrollTop + 50 || top > scrollTop + containerHeight - 50) {
                 scrollContainer.scrollTo({
                    top: Math.max(0, top - (containerHeight / 2)),
                    behavior: 'smooth'
                });
            }
        }
    }

    // Variable rendering cache for incremental updates
    let variableCache = {};

    function renderVariables(locals, prevLocals) {
        if (!dom.variablesContainer) return;
        
        if (!locals || Object.keys(locals).length === 0) {
            dom.variablesContainer.innerHTML = `
                <div style="color: #484f58; text-align: center; margin-top: 20px;">
                    当前作用域无变量
                </div>`;
            variableCache = {};
            return;
        }

        const currentKeys = new Set(Object.keys(locals));
        const cachedKeys = new Set(Object.keys(variableCache));
        
        // Remove variables that no longer exist
        for (const key of cachedKeys) {
            if (!currentKeys.has(key)) {
                const el = document.getElementById(`var-${key}`);
                if (el) el.remove();
                delete variableCache[key];
            }
        }

        // Update or add variables
        const sortedKeys = Object.keys(locals).sort();
        
        for (const key of sortedKeys) {
            const value = locals[key];
            const prevValue = prevLocals ? prevLocals[key] : undefined;
            const cachedValue = variableCache[key];
            
            const isChanged = prevValue !== undefined && JSON.stringify(value) !== JSON.stringify(prevValue);
            const isNew = prevValue === undefined;
            const valueChanged = !cachedValue || JSON.stringify(value) !== JSON.stringify(cachedValue);
            
            // Skip if value hasn't changed
            if (!valueChanged && !isChanged) continue;
            
            // Update cache
            variableCache[key] = value;
            
            // Get or create element
            let item = document.getElementById(`var-${key}`);
            if (!item) {
                item = document.createElement('div');
                item.id = `var-${key}`;
                item.className = 'var-item';
                dom.variablesContainer.appendChild(item);
            }
            
            // Update content efficiently
            item.className = `var-item ${isChanged || isNew ? 'changed' : ''}`;
            
            item.innerHTML = `
                <div class="var-header">
                    <span class="var-name">${escapeHtml(key)}</span>
                    <span class="var-type">${determineType(value)}</span>
                </div>
                <div class="var-value-container ${isChanged ? 'value-changed' : ''}">
                    ${renderValueContent(value, prevValue)}
                </div>
            `;
        }

        // Reorder elements to match sorted keys
        const sortedElements = sortedKeys.map(key => document.getElementById(`var-${key}`)).filter(Boolean);
        sortedElements.forEach((el, i) => {
            if (dom.variablesContainer.children[i] !== el) {
                dom.variablesContainer.appendChild(el);
            }
        });
    }

    function renderValueContent(value, prevValue) {
        if (Array.isArray(value)) {
            const items = value.slice(0, 50).map((val, idx) => {
                if (val === "<Truncated...>") return '<span class="array-truncated">...</span>';
                const changed = Array.isArray(prevValue) && prevValue[idx] !== val;
                return `
                    <div class="array-cell ${changed ? 'cell-changed' : ''}">
                        <div class="array-index">${idx}</div>
                        <span class="array-val">${formatValue(val)}</span>
                    </div>
                `;
            }).join('');
            return `<div class="array-viz">${items}</div>`;
        } else if (typeof value === 'object' && value !== null) {
            const isEmpty = Object.keys(value).length === 0;
            return `<pre style="margin:0;color:#79c0ff">${isEmpty ? '{}' : escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
        } else {
            return formatValue(value);
        }
    }
    
    function determineType(val) {
        if (val === null) return 'NoneType';
        if (Array.isArray(val)) return `List[${val.length}]`;
        return typeof val;
    }
    
    function formatValue(val) {
        if (typeof val === 'string') return `"${val}"`;
        if (typeof val === 'object' && val !== null) {
            if (Array.isArray(val)) return `[${val.length} items]`;
            return `{...}`;
        }
        return String(val);
    }

    function renderStepInsight(step, prevStep) {
        if (!dom.insightText) return;
        
        let insight = "";
        
        if (!prevStep) {
            insight = `<div class="insight-header"><i class="ri-flag-fill"></i> 程序启动</div>`;
            insight += `<div class="insight-body">初始化全局执行上下文。</div>`;
        } else {
            // 1. Analyze AST Context
            const typeMap = {
                'Assign': { icon: 'ri-pencil-fill', label: '变量赋值', desc: '正在计算表达式并将结果赋值给变量。' },
                'AugAssign': { icon: 'ri-pencil-fill', label: '增量赋值', desc: '正在更新变量的值。' },
                'AnnAssign': { icon: 'ri-pencil-fill', label: '变量声明', desc: '声明变量类型并赋值。' },
                'For': { icon: 'ri-repeat-fill', label: '循环迭代', desc: '进入循环或更新迭代变量。' },
                'While': { icon: 'ri-repeat-fill', label: '循环判断', desc: '检查循环条件是否满足。' },
                'If': { icon: 'ri-question-fill', label: '条件判断', desc: '评估条件表达式以决定执行路径。' },
                'FunctionDef': { icon: 'ri-function-fill', label: '函数定义', desc: '定义新函数（跳过函数体）。' },
                'Return': { icon: 'ri-logout-box-r-fill', label: '函数返回', desc: '结束函数执行并返回结果。' },
                'Call': { icon: 'ri-function-line', label: '函数调用', desc: '调用函数或方法。' },
                'Expr': { icon: 'ri-code-line', label: '表达式', desc: '执行表达式（如打印或副作用）。' },
                'Import': { icon: 'ri-download-cloud-fill', label: '导入模块', desc: '加载外部库或模块。' },
                'ImportFrom': { icon: 'ri-download-cloud-fill', label: '导入对象', desc: '从模块中导入特定对象。' }
            };

            const stmtType = step.stmt_type || 'Unknown';
            const info = typeMap[stmtType] || { icon: 'ri-cursor-fill', label: '执行语句', desc: '执行当前代码行。' };
            
            insight = `<div class="insight-header"><i class="${info.icon}"></i> ${info.label} <span style="opacity:0.6; font-weight:normal; font-size: 12px; margin-left: 8px;">Line ${step.line_no}</span></div>`;
            
            // 2. Analyze Variable Changes
            const changes = [];
            const locals = step.locals || {};
            const prevLocals = prevStep.locals || {};
            
            for (const key in locals) {
                if (key.startsWith('__')) continue;
                
                const val = locals[key];
                const prevVal = prevLocals[key];
                
                if (JSON.stringify(val) !== JSON.stringify(prevVal)) {
                    if (prevVal === undefined) {
                        changes.push(`初始化 <code>${key}</code> 为 <span class="val-highlight">${formatValue(val)}</span>`);
                    } else {
                        // Array smart diff
                        if (Array.isArray(val) && Array.isArray(prevVal)) {
                             const diffs = [];
                             val.forEach((v, i) => {
                                 if (prevVal[i] !== v) diffs.push(`[${i}] ${formatValue(prevVal[i])} ➝ ${formatValue(v)}`);
                             });
                             
                             if (diffs.length > 0) {
                                 changes.push(`更新列表 <code>${key}</code>: ${diffs.join(", ")}`);
                             } else if (val.length !== prevVal.length) {
                                 changes.push(`列表 <code>${key}</code> 长度变为 ${val.length}`);
                             } else {
                                 changes.push(`列表 <code>${key}</code> 内容已更新`);
                             }
                        } else {
                             changes.push(`<code>${key}</code>: <span class="val-old">${formatValue(prevVal)}</span> ➝ <span class="val-new">${formatValue(val)}</span>`);
                        }
                    }
                }
            }
            
            insight += `<div class="insight-body">`;
            if (changes.length > 0) {
                insight += changes.map(c => `<div class="change-item"><i class="ri-flashlight-fill" style="color:#ffd60a"></i> ${c}</div>`).join("");
            } else {
                // If no variable changes, use the generic description or control flow logic
                if (stmtType === 'If' || stmtType === 'While') {
                     // Check if line jumped
                     if (step.line_no > prevStep.line_no + 1) {
                         insight += `<div class="change-item">条件为 <b>False</b>，跳过代码块。</div>`;
                     } else {
                         insight += `<div class="change-item">条件为 <b>True</b>，进入代码块。</div>`;
                     }
                } else {
                     insight += `<div class="change-item" style="opacity: 0.7">${info.desc}</div>`;
                }
            }
            insight += `</div>`;
        }
        
        dom.insightText.innerHTML = insight;
    }

    function updateConsole(currentTime) {
        if (!dom.consoleLastLine) return;
        
        const logs = state.capturedOutput.filter(log => log.timestamp <= currentTime + 0.05);
        if (logs.length > 0) {
            const lastLog = logs[logs.length - 1];
            dom.consoleLastLine.textContent = lastLog.content.trim() || " ";
        }
    }

    // ==========================================
    // Controls & Navigation
    // ==========================================
    function setupEventListeners() {
        // Playback
        if (dom.btnPlayPause) {
            dom.btnPlayPause.addEventListener('click', togglePlay);
        }

        ['btn-prev', 'btn-next', 'btn-start', 'btn-end'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', () => {
                    pause();
                    if (id === 'btn-prev') updateState(state.currentStep - 1);
                    if (id === 'btn-next') updateState(state.currentStep + 1);
                    if (id === 'btn-start') updateState(0);
                    if (id === 'btn-end') updateState(state.traceData.length - 1);
                });
            }
        });

        if (dom.timelineSlider) {
            dom.timelineSlider.addEventListener('input', (e) => {
                pause();
                updateState(parseInt(e.target.value));
            });
        }

        // Keyboard
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                pause();
                updateState(state.currentStep - 1);
            } else if (e.key === 'ArrowRight') {
                pause();
                updateState(state.currentStep + 1);
            } else if (e.key === ' ') {
                e.preventDefault();
                togglePlay();
            } else if (e.key === 'b' || e.key === 'B') {
                if (!e.ctrlKey && !e.metaKey) {
                    toggleBreakpointMode();
                }
            } else if (e.key === 'n' || e.key === 'N') {
                if (!e.ctrlKey && !e.metaKey) {
                    skipToNextBreakpoint();
                }
            } else if (e.key === 'Home') {
                pause();
                updateState(0);
            } else if (e.key === 'End') {
                pause();
                updateState(state.traceData.length - 1);
            }
        });

        // Breakpoint mode button
        if (dom.breakpointModeBtn) {
            dom.breakpointModeBtn.addEventListener('click', toggleBreakpointMode);
        }

        // Line number click for breakpoints
        if (dom.lineNumbersContainer) {
            dom.lineNumbersContainer.addEventListener('click', (e) => {
                const lineNum = e.target.closest('.line-num');
                if (lineNum) {
                    const lineNo = parseInt(lineNum.id.replace('line-num-', ''));
                    if (!isNaN(lineNo)) {
                        toggleBreakpoint(lineNo);
                    }
                }
            });
        }
    }

    // ==========================================
    // Breakpoint System
    // ==========================================
    function toggleBreakpointMode() {
        state.breakpointMode = !state.breakpointMode;
        if (dom.breakpointModeBtn) {
            dom.breakpointModeBtn.classList.toggle('active', state.breakpointMode);
            dom.breakpointModeBtn.innerHTML = state.breakpointMode 
                ? ICONS.BREAKPOINT_ON 
                : ICONS.BREAKPOINT_OFF;
        }
        updateBreakpointCount();
    }

    function toggleBreakpoint(lineNo) {
        if (state.breakpoints.has(lineNo)) {
            state.breakpoints.delete(lineNo);
        } else {
            state.breakpoints.add(lineNo);
        }
        updateLineNumbersWithBreakpoints();
        updateBreakpointCount();
    }

    function updateBreakpointCount() {
        if (dom.breakpointCount) {
            const count = state.breakpoints.size;
            dom.breakpointCount.textContent = count;
            dom.breakpointCount.classList.toggle('visible', count > 0);
        }
    }

    function updateLineNumbersWithBreakpoints() {
        document.querySelectorAll('.line-num').forEach(el => {
            const lineNo = parseInt(el.id.replace('line-num-', ''));
            if (!isNaN(lineNo)) {
                el.classList.toggle('breakpoint', state.breakpoints.has(lineNo));
            }
        });
    }

    function skipToNextBreakpoint() {
        if (state.breakpoints.size === 0) return;
        
        const sortedBreakpoints = Array.from(state.breakpoints).sort((a, b) => a - b);
        const currentLine = state.traceData[state.currentStep]?.line_no;
        
        // Find next breakpoint
        for (let i = state.currentStep + 1; i < state.traceData.length; i++) {
            const step = state.traceData[i];
            if (state.breakpoints.has(step.line_no)) {
                updateState(i);
                // Highlight breakpoint hit
                const lineEl = document.getElementById(`line-num-${step.line_no}`);
                if (lineEl) {
                    lineEl.classList.add('breakpoint-hit');
                    setTimeout(() => lineEl.classList.remove('breakpoint-hit'), 500);
                }
                return;
            }
        }
        
        // If no breakpoint found after current, wrap around
        for (let i = 0; i < state.currentStep; i++) {
            const step = state.traceData[i];
            if (state.breakpoints.has(step.line_no)) {
                updateState(i);
                return;
            }
        }
    }

    function shouldPauseAtBreakpoint(stepIndex) {
        if (!state.isPlaying) return false;
        const step = state.traceData[stepIndex];
        return step && state.breakpoints.has(step.line_no);
    }

    // Enhanced play function with breakpoint support
    function play() {
        if (state.isPlaying) return;
        state.isPlaying = true;
        if (dom.btnPlayPause) dom.btnPlayPause.innerHTML = ICONS.PAUSE;
        
        if (state.currentStep >= state.traceData.length - 1) {
            state.currentStep = -1;
        }
        
        state.playInterval = setInterval(() => {
            if (state.currentStep < state.traceData.length - 1) {
                const nextStep = state.currentStep + 1;
                
                // Check for breakpoint
                if (shouldPauseAtBreakpoint(nextStep)) {
                    updateState(nextStep);
                    pause();
                    // Visual feedback
                    const lineEl = document.getElementById(`line-num-${state.traceData[nextStep].line_no}`);
                    if (lineEl) {
                        lineEl.classList.add('breakpoint-hit');
                        setTimeout(() => lineEl.classList.remove('breakpoint-hit'), 500);
                    }
                    return;
                }
                
                updateState(nextStep);
            } else {
                pause();
            }
        }, state.playSpeed);
    }

    function pause() {
        if (!state.isPlaying) return;
        state.isPlaying = false;
        if (dom.btnPlayPause) dom.btnPlayPause.innerHTML = ICONS.PLAY;
        clearInterval(state.playInterval);
    }

    function togglePlay() {
        if (state.isPlaying) pause(); else play();
    }

    function updateStatus(text, className) {
        if (dom.statusText) {
            dom.statusText.textContent = text;
            // dom.statusText.className = 'status-val ' + className;
        }
    }

    // Start
    init();
});
