/**
 * ChronoTrace Onboarding System
 * Multi-page onboarding experience
 */
class Onboarding {
    constructor(page = 'index') {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.spotlight = null;
        this.isActive = false;
        this.page = page;
        this.storageKey = `chronotrace_onboarding_${page}`;
        
        // Page-specific steps
        this.pageSteps = {
            index: this.getIndexSteps(),
            editor: this.getEditorSteps(),
            memory: this.getMemorySteps(),
            visualizer: this.getVisualizerSteps(),
            compare: this.getCompareSteps(),
            source: this.getSourceSteps()
        };
    }

    // Index/Dashboard steps
    getIndexSteps() {
        return [
            {
                id: 'welcome',
                type: 'modal',
                title: '欢迎使用 HUAYCODE',
                subtitle: 'Python 代码执行可视化引擎',
                content: '通过先进的追踪技术，让每一行代码的执行过程都清晰可见。',
                features: [
                    { icon: 'ri-code-s-slash-line', text: '逐行执行追踪' },
                    { icon: 'ri-line-chart-line', text: '内存分析可视化' },
                    { icon: 'ri-bar-chart-grouped-line', text: '算法动态演示' }
                ],
                cta: '开始体验',
                skip: '跳过引导'
            },
            {
                id: 'sidebar',
                target: '.sidebar-nav',
                type: 'spotlight',
                title: '导航侧边栏',
                content: '在这里切换不同的功能模块。每个模块都专注于特定的分析场景。',
                position: 'right'
            },
            {
                id: 'playback',
                target: '.playback-group',
                type: 'spotlight',
                title: '播放控制',
                content: '控制代码执行的播放进度。支持上一步、下一步、播放/暂停等操作。',
                position: 'bottom',
                shortcuts: ['← 上一步', '→ 下一步', 'Space 播放/暂停']
            },
            {
                id: 'timeline',
                target: '.timeline-wrapper',
                type: 'spotlight',
                title: '执行时间轴',
                content: '拖动时间轴快速跳转到任意执行步骤。',
                position: 'bottom'
            },
            {
                id: 'variables',
                target: '.data-view-panel',
                type: 'spotlight',
                title: '变量监视',
                content: '实时查看变量值的变化。数组会以可视化方式展示。',
                position: 'left'
            },
            {
                id: 'complete',
                type: 'modal',
                title: '控制台就绪！',
                subtitle: '您已了解控制台基本功能',
                content: '前往代码编辑器运行代码，然后回到这里查看执行过程。',
                tips: [
                    '使用算法库快速加载示例代码',
                    '按 ? 随时查看帮助'
                ],
                cta: '开始使用'
            }
        ];
    }

    // Editor steps
    getEditorSteps() {
        return [
            {
                id: 'editor-welcome',
                type: 'modal',
                title: '代码编辑器',
                subtitle: '编写和运行 Python 代码',
                content: '在这里编写代码并进行追踪分析。支持语法高亮、自动补全等功能。',
                features: [
                    { icon: 'ri-play-fill', text: '一键运行并追踪' },
                    { icon: 'ri-book-2-line', text: '内置算法库' },
                    { icon: 'ri-arrow-go-back-line', text: '撤销/重做支持' }
                ],
                cta: '继续'
            },
            {
                id: 'snippet-lib',
                target: '#snippet-selector',
                type: 'spotlight',
                title: '算法库',
                content: '点击打开算法库，快速加载经典算法代码。支持搜索功能。',
                position: 'bottom'
            },
            {
                id: 'undo-redo',
                target: '#btn-undo',
                type: 'spotlight',
                title: '撤销/重做',
                content: '撤销或重做代码修改。快捷键: Ctrl+Z / Ctrl+Y',
                position: 'bottom',
                shortcuts: ['Ctrl+Z 撤销', 'Ctrl+Y 重做']
            },
            {
                id: 'run-btn',
                target: '#btn-run',
                type: 'spotlight',
                title: '运行代码',
                content: '点击此按钮执行代码并开始追踪。执行完成后会自动跳转到控制台。',
                position: 'bottom',
                shortcuts: ['Ctrl+Enter 运行']
            },
            {
                id: 'editor-complete',
                type: 'modal',
                title: '编辑器就绪！',
                content: '现在可以开始编写代码并进行分析了。',
                tips: [
                    '从算法库选择一个示例开始',
                    '使用 Ctrl+Enter 快速运行'
                ],
                cta: '开始编码'
            }
        ];
    }

    // Memory analysis steps
    getMemorySteps() {
        return [
            {
                id: 'memory-welcome',
                type: 'modal',
                title: '内存分析',
                subtitle: '深度分析代码内存消耗',
                content: '查看代码执行过程中的内存使用情况，定位内存热点。',
                features: [
                    { icon: 'ri-line-chart-line', text: '内存趋势图' },
                    { icon: 'ri-fire-line', text: '热点分析' },
                    { icon: 'ri-timer-line', text: '时间统计' }
                ],
                cta: '继续'
            },
            {
                id: 'memory-stats',
                target: '.stats-grid',
                type: 'spotlight',
                title: '内存统计卡片',
                content: '显示峰值内存、当前占用和平均消耗三个关键指标。',
                position: 'bottom'
            },
            {
                id: 'memory-chart',
                target: '.chart-section',
                type: 'spotlight',
                title: '内存趋势图',
                content: '可视化展示内存随时间的变化趋势。可通过采样按钮调整显示精度。',
                position: 'top'
            },
            {
                id: 'memory-hotspots',
                target: '#hotspots-list',
                type: 'spotlight',
                title: '内存热点',
                content: '显示内存消耗最多的5行代码，帮助定位优化目标。',
                position: 'top'
            },
            {
                id: 'memory-time',
                target: '#time-hotspots-list',
                type: 'spotlight',
                title: '时间热点',
                content: '显示执行时间最长的5行代码，帮助分析性能瓶颈。',
                position: 'top'
            },
            {
                id: 'memory-complete',
                type: 'modal',
                title: '内存分析就绪！',
                content: '运行代码后即可查看详细的内存分析报告。',
                tips: [
                    '峰值内存过高可能存在内存泄漏',
                    '热点行是优化的重点',
                    '调整采样率优化图表性能'
                ],
                cta: '开始使用'
            }
        ];
    }

    // Visualizer steps
    getVisualizerSteps() {
        return [
            {
                id: 'viz-welcome',
                type: 'modal',
                title: '算法可视化',
                subtitle: '动态演示算法执行过程',
                content: '通过动画直观展示排序、搜索等算法的执行过程。',
                features: [
                    { icon: 'ri-play-fill', text: '自动播放' },
                    { icon: 'ri-speed-line', text: '速度调节' },
                    { icon: 'ri-volume-up-line', text: '音效反馈' }
                ],
                cta: '继续'
            },
            {
                id: 'viz-playback',
                target: '.playback-group',
                type: 'spotlight',
                title: '播放控制',
                content: '控制动画播放。支持上一步、播放/暂停、下一步操作。',
                position: 'bottom',
                shortcuts: ['← 上一步', '→ 下一步', 'Space 播放']
            },
            {
                id: 'viz-timeline',
                target: '.timeline-wrapper',
                type: 'spotlight',
                title: '执行进度',
                content: '显示当前执行步骤，可拖动滑块快速跳转。',
                position: 'bottom'
            },
            {
                id: 'viz-stage',
                target: '.stage-container',
                type: 'spotlight',
                title: '可视化舞台',
                content: '数组以柱状图形式动态展示，交换操作会有动画效果。',
                position: 'left'
            },
            {
                id: 'viz-stats',
                target: '.stats-overlay',
                type: 'spotlight',
                title: '统计信息',
                content: '实时显示比较次数、交换次数和数组访问次数。',
                position: 'bottom'
            },
            {
                id: 'viz-complete',
                type: 'modal',
                title: '可视化就绪！',
                content: '从编辑器运行排序算法，即可看到动态演示效果。',
                tips: [
                    '选择一个排序算法运行',
                    '使用热力图查看访问频率',
                    '开启音效增强体验'
                ],
                cta: '开始使用'
            }
        ];
    }

    // Compare steps
    getCompareSteps() {
        return [
            {
                id: 'compare-welcome',
                type: 'modal',
                title: '执行对比',
                subtitle: '对比两次代码执行的差异',
                content: '分析不同执行之间的变量变化、内存消耗和执行路径差异。',
                features: [
                    { icon: 'ri-braces-line', text: '变量差异' },
                    { icon: 'ri-file-code-line', text: '覆盖率对比' },
                    { icon: 'ri-route-line', text: '路径分析' }
                ],
                cta: '继续'
            },
            {
                id: 'compare-card-a',
                target: '#card-a',
                type: 'spotlight',
                title: '基准执行 (A)',
                content: '选择作为基准的执行记录。显示执行时间、步骤数和峰值内存。',
                position: 'right'
            },
            {
                id: 'compare-swap',
                target: '#btn-swap',
                type: 'spotlight',
                title: '交换按钮',
                content: '点击可快速交换A和B的选择。',
                position: 'bottom'
            },
            {
                id: 'compare-card-b',
                target: '#card-b',
                type: 'spotlight',
                title: '对比执行 (B)',
                content: '选择要与基准对比的执行记录。',
                position: 'left'
            },
            {
                id: 'compare-btn',
                target: '#btn-compare',
                type: 'spotlight',
                title: '开始对比',
                content: '选择两次执行后，点击此按钮开始分析差异。',
                position: 'top'
            },
            {
                id: 'compare-complete',
                type: 'modal',
                title: '对比功能就绪！',
                content: '多次运行代码后即可使用对比功能分析差异。',
                tips: [
                    '在编辑器中多次运行代码',
                    '选择两次执行进行对比',
                    '查看变量、内存、路径差异'
                ],
                cta: '开始使用'
            }
        ];
    }

    // Source overview steps
    getSourceSteps() {
        return [
            {
                id: 'source-welcome',
                type: 'modal',
                title: '源码概览',
                subtitle: '查看代码执行覆盖情况',
                content: '直观展示哪些代码行被执行过，帮助理解代码运行路径。',
                features: [
                    { icon: 'ri-code-s-slash-line', text: '代码高亮显示' },
                    { icon: 'ri-mark-pen-line', text: '执行行标记' },
                    { icon: 'ri-map-2-line', text: '小地图导航' }
                ],
                cta: '继续'
            },
            {
                id: 'source-header',
                target: '.source-header',
                type: 'spotlight',
                title: '文件信息',
                content: '显示当前查看的源文件名称和路径。',
                position: 'bottom'
            },
            {
                id: 'source-code',
                target: '.source-content',
                type: 'spotlight',
                title: '代码区域',
                content: '显示完整的源代码，被执行过的行会高亮标记。',
                position: 'left'
            },
            {
                id: 'source-minimap',
                target: '.minimap',
                type: 'spotlight',
                title: '小地图',
                content: '提供代码全局视图，快速定位到目标位置。',
                position: 'left'
            },
            {
                id: 'source-complete',
                type: 'modal',
                title: '源码概览就绪！',
                content: '运行代码后即可查看执行覆盖情况。',
                tips: [
                    '高亮行表示被执行过',
                    '使用小地图快速导航',
                    '点击复制按钮复制源码'
                ],
                cta: '开始使用'
            }
        ];
    }

    // Settings steps
    getSettingsSteps() {
        return [
            {
                id: 'settings-welcome',
                type: 'modal',
                title: '系统设置',
                subtitle: '自定义 HUAYCODE 行为',
                content: '调整播放速度、界面效果等各项参数。',
                features: [
                    { icon: 'ri-speed-line', text: '播放速度调节' },
                    { icon: 'ri-keyboard-line', text: '快捷键查看' },
                    { icon: 'ri-refresh-line', text: '一键重置' }
                ],
                cta: '继续'
            },
            {
                id: 'settings-speed',
                target: '#speed-slider',
                type: 'spotlight',
                title: '执行延迟',
                content: '拖动滑块调整代码执行的播放速度。值越小播放越快。',
                position: 'bottom'
            },
            {
                id: 'settings-scroll',
                target: '#auto-scroll-toggle',
                type: 'spotlight',
                title: '自动滚动',
                content: '开启后，代码执行时会自动将高亮行保持在视图中心。',
                position: 'bottom'
            },
            {
                id: 'settings-animation',
                target: '#anim-toggle',
                type: 'spotlight',
                title: '动画效果',
                content: '控制界面过渡动画和视觉效果的开关。',
                position: 'bottom'
            },
            {
                id: 'settings-shortcuts',
                target: '.shortcuts-grid',
                type: 'spotlight',
                title: '快捷键列表',
                content: '查看所有可用的键盘快捷键，提高操作效率。',
                position: 'top'
            },
            {
                id: 'settings-complete',
                type: 'modal',
                title: '设置页面就绪！',
                content: '根据您的习惯调整各项设置。',
                tips: [
                    '新手建议设置较慢的播放速度',
                    '记住常用快捷键提高效率',
                    '可随时重置恢复默认设置'
                ],
                cta: '开始使用'
            }
        ];
    }

    init(steps = null) {
        this.steps = steps || this.pageSteps[this.page] || this.pageSteps.index;
        
        // Clean up any existing elements first
        this.cleanupExistingElements();
        
        // Only create overlay if not completed and has steps
        if (!this.isCompleted() && this.steps && this.steps.length > 0) {
            this.createStyles();
            this.createOverlay();
            setTimeout(() => this.start(), 500);
        }
    }

    cleanupExistingElements() {
        const ids = [
            'onboarding-overlay',
            'onboarding-spotlight', 
            'onboarding-tooltip',
            'onboarding-modal',
            'onboarding-step-indicator',
            'onboarding-styles'
        ];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.remove();
        });
    }

    createStyles() {
        if (document.getElementById('onboarding-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'onboarding-styles';
        style.textContent = `
            .onboarding-overlay {
                position: fixed;
                inset: 0;
                background: transparent;
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: none;
            }
            .onboarding-overlay.active {
                opacity: 1;
                pointer-events: none;
            }
            .onboarding-spotlight {
                position: absolute;
                background: transparent;
                border-radius: 12px;
                box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.9), 0 0 0 9999px rgba(0, 0, 0, 0.5);
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: none;
                z-index: 10000;
            }
            .onboarding-spotlight::before {
                content: '';
                position: absolute;
                inset: -4px;
                border-radius: 16px;
                border: 2px solid rgba(10, 132, 255, 0.7);
                animation: spotlightPulse 2s infinite;
            }
            @keyframes spotlightPulse {
                0%, 100% { border-color: rgba(10, 132, 255, 0.7); box-shadow: 0 0 15px rgba(10, 132, 255, 0.4); }
                50% { border-color: rgba(10, 132, 255, 1); box-shadow: 0 0 25px rgba(10, 132, 255, 0.6); }
            }
            .onboarding-modal {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.9);
                background: linear-gradient(135deg, rgba(28, 28, 30, 0.95) 0%, rgba(44, 44, 46, 0.95) 100%);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 24px;
                padding: 48px;
                max-width: 480px;
                width: 90%;
                z-index: 10003;
                opacity: 0;
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6), 0 0 40px rgba(10, 132, 255, 0.2);
                backdrop-filter: blur(20px);
                pointer-events: auto !important;
            }
            .onboarding-modal.active {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
            .onboarding-modal::before {
                content: '';
                position: absolute;
                inset: 0;
                border-radius: 24px;
                background: radial-gradient(circle at 30% 20%, rgba(10, 132, 255, 0.15) 0%, transparent 50%);
                pointer-events: none;
            }
            .modal-badge {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.3);
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                color: #0a84ff;
                margin-bottom: 24px;
            }
            .modal-title {
                font-size: 32px;
                font-weight: 700;
                background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 8px;
                line-height: 1.2;
            }
            .modal-subtitle {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 24px;
            }
            .modal-features {
                display: flex;
                flex-direction: column;
                gap: 16px;
                margin: 32px 0;
            }
            .feature-item {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 16px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                transition: all 0.3s;
            }
            .feature-item:hover {
                background: rgba(255, 255, 255, 0.06);
                transform: translateX(4px);
            }
            .feature-icon {
                width: 44px;
                height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(10, 132, 255, 0.15);
                border-radius: 12px;
                color: #0a84ff;
                font-size: 20px;
            }
            .feature-text {
                font-size: 14px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.9);
            }
            .modal-tips {
                margin: 24px 0;
                padding: 20px;
                background: rgba(255, 215, 0, 0.08);
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: 12px;
            }
            .tip-title {
                font-size: 12px;
                font-weight: 700;
                color: #ffd60a;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
            }
            .tip-item {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 8px;
            }
            .tip-item:last-child { margin-bottom: 0; }
            .tip-item i { color: #ffd60a; font-size: 14px; }
            .modal-cta {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #0a84ff 0%, #0056d2 100%);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 4px 20px rgba(10, 132, 255, 0.4);
            }
            .modal-cta:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(10, 132, 255, 0.5);
            }
            .modal-skip {
                display: block;
                margin-top: 16px;
                text-align: center;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.4);
                background: none;
                border: none;
                cursor: pointer;
            }
            .modal-skip:hover { color: rgba(255, 255, 255, 0.7); }
            .onboarding-tooltip {
                position: fixed;
                background: linear-gradient(135deg, rgba(28, 28, 30, 0.95) 0%, rgba(44, 44, 46, 0.95) 100%);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px;
                padding: 24px;
                max-width: 320px;
                min-width: 280px;
                z-index: 10003;
                opacity: 0;
                transform: translateY(10px);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 30px rgba(10, 132, 255, 0.15);
                backdrop-filter: blur(20px);
                pointer-events: auto !important;
            }
            .onboarding-tooltip.active {
                opacity: 1;
                transform: translateY(0);
            }
            .onboarding-tooltip::before {
                content: '';
                position: absolute;
                width: 12px;
                height: 12px;
                background: rgba(28, 28, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.15);
                transform: rotate(45deg);
            }
            .onboarding-tooltip.position-right::before { left: -7px; top: 24px; border-right: none; border-top: none; }
            .onboarding-tooltip.position-left::before { right: -7px; top: 24px; border-left: none; border-bottom: none; }
            .onboarding-tooltip.position-bottom::before { top: -7px; left: 24px; border-bottom: none; border-left: none; }
            .onboarding-tooltip.position-top::before { bottom: -7px; left: 24px; border-top: none; border-right: none; }
            .tooltip-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
            }
            .tooltip-title {
                font-size: 18px;
                font-weight: 700;
                color: #fff;
            }
            .tooltip-step {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.4);
                padding: 4px 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
            .tooltip-content {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                line-height: 1.6;
                margin-bottom: 16px;
            }
            .tooltip-shortcuts {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 16px;
            }
            .shortcut-tag {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 10px;
                background: rgba(10, 132, 255, 0.1);
                border: 1px solid rgba(10, 132, 255, 0.2);
                border-radius: 6px;
                font-size: 11px;
                color: #0a84ff;
            }
            .tooltip-actions {
                display: flex;
                gap: 12px;
            }
            .tooltip-btn-primary {
                flex: 1;
                padding: 12px;
                background: #0a84ff;
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            .tooltip-btn-primary:hover { background: #0071e3; }
            .tooltip-btn-secondary {
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .tooltip-btn-secondary:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }
            .tooltip-progress {
                display: flex;
                gap: 6px;
                margin-top: 16px;
                justify-content: center;
            }
            .progress-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.2);
                transition: all 0.3s;
            }
            .progress-dot.active { background: #0a84ff; transform: scale(1.2); }
            .progress-dot.completed { background: #30d158; }
            .onboarding-step-indicator {
                position: fixed;
                bottom: 24px;
                right: 24px;
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 20px;
                background: rgba(28, 28, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                backdrop-filter: blur(10px);
                z-index: 10002;
                opacity: 0;
                transform: translateY(20px);
                transition: all 0.3s;
            }
            .onboarding-step-indicator.active { opacity: 1; transform: translateY(0); }
            .step-indicator-text { font-size: 13px; color: rgba(255, 255, 255, 0.6); }
            .step-indicator-text strong { color: #0a84ff; }
            .step-indicator-skip {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.4);
                background: none;
                border: none;
                cursor: pointer;
            }
            .step-indicator-skip:hover { color: #fff; }
            .onboarding-highlight {
                position: relative !important;
                z-index: 10001 !important;
                background: rgba(255, 255, 255, 0.05) !important;
                border-radius: 8px !important;
            }
            .onboarding-highlight::after {
                content: '';
                position: absolute;
                inset: -2px;
                border-radius: 10px;
                border: 2px solid rgba(10, 132, 255, 0.8);
                pointer-events: none;
                animation: highlightPulse 1.5s infinite;
            }
            @keyframes highlightPulse {
                0%, 100% { box-shadow: 0 0 10px rgba(10, 132, 255, 0.3); }
                50% { box-shadow: 0 0 20px rgba(10, 132, 255, 0.6); }
            }
        `;
        document.head.appendChild(style);
    }

    createOverlay() {
        const existingIds = ['onboarding-overlay', 'onboarding-spotlight', 'onboarding-tooltip', 'onboarding-modal', 'onboarding-step-indicator'];
        existingIds.forEach(id => {
            const existing = document.getElementById(id);
            if (existing) existing.remove();
        });

        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay';
        this.overlay.id = 'onboarding-overlay';
        
        this.spotlight = document.createElement('div');
        this.spotlight.className = 'onboarding-spotlight';
        this.spotlight.id = 'onboarding-spotlight';
        this.spotlight.style.display = 'none';
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'onboarding-tooltip';
        this.tooltip.id = 'onboarding-tooltip';
        
        this.modal = document.createElement('div');
        this.modal.className = 'onboarding-modal';
        this.modal.id = 'onboarding-modal';

        this.stepIndicator = document.createElement('div');
        this.stepIndicator.className = 'onboarding-step-indicator';
        this.stepIndicator.id = 'onboarding-step-indicator';

        document.body.appendChild(this.overlay);
        document.body.appendChild(this.spotlight);
        document.body.appendChild(this.tooltip);
        document.body.appendChild(this.modal);
        document.body.appendChild(this.stepIndicator);
    }

    start() {
        if (!this.overlay) {
            this.createStyles();
            this.createOverlay();
        }
        
        this.currentStep = 0;
        this.isActive = true;
        
        // Keyboard support
        this._keyHandler = (e) => {
            if (!this.isActive) return;
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.nextStep();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.complete();
            }
        };
        document.addEventListener('keydown', this._keyHandler);
        
        if (this.overlay) {
            this.overlay.classList.add('active');
        }
        
        this.showStep(this.currentStep);
    }

    showStep(index) {
        console.log('[Onboarding] showStep called with index:', index, 'steps.length:', this.steps.length);
        if (index >= this.steps.length) {
            console.log('[Onboarding] Calling complete() because index >= steps.length');
            this.complete();
            return;
        }

        const step = this.steps[index];
        this.currentStep = index;

        // Clear any pending tooltip build timeout
        if (this._tooltipTimeout) {
            clearTimeout(this._tooltipTimeout);
            this._tooltipTimeout = null;
        }

        // Clear highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
            el.style.zIndex = '';
        });

        this.tooltip.classList.remove('active');
        this.tooltip.style.display = 'none';
        this.tooltip.style.pointerEvents = 'none';
        this.modal.classList.remove('active');
        this.modal.style.display = 'none';
        this.modal.style.pointerEvents = 'none';
        this.spotlight.style.display = 'none';

        if (step.type === 'modal') {
            this.modal.style.display = '';
            this.modal.style.pointerEvents = 'auto';
            this.showModal(step);
        } else if (step.type === 'spotlight') {
            this.tooltip.style.display = '';
            this.tooltip.style.pointerEvents = 'auto';
            this.showSpotlight(step);
        }

        this.updateStepIndicator();
    }

    showModal(step) {
        console.log('[Onboarding] showModal called for step:', step.id);
        let featuresHtml = '';
        if (step.features) {
            featuresHtml = `<div class="modal-features">${step.features.map(f => `
                <div class="feature-item">
                    <div class="feature-icon"><i class="${f.icon}"></i></div>
                    <span class="feature-text">${f.text}</span>
                </div>`).join('')}</div>`;
        }

        let tipsHtml = '';
        if (step.tips) {
            tipsHtml = `<div class="modal-tips">
                <div class="tip-title">小贴士</div>
                ${step.tips.map(t => `<div class="tip-item"><i class="ri-lightbulb-line"></i><span>${t}</span></div>`).join('')}
            </div>`;
        }

        this.modal.innerHTML = `
            <div class="modal-badge"><i class="ri-rocket-line"></i> HUAYCODE Pro</div>
            <h2 class="modal-title">${step.title}</h2>
            <p class="modal-subtitle">${step.subtitle || ''}</p>
            <p class="tooltip-content">${step.content}</p>
            ${featuresHtml}
            ${tipsHtml}
            <button class="modal-cta" id="onboarding-cta">${step.cta || '继续'}</button>
            <button class="modal-skip" id="onboarding-skip">${step.skip || '跳过引导'}</button>
        `;

        // Ensure tooltip is completely hidden and not blocking clicks
        this.tooltip.classList.remove('active');
        this.tooltip.style.display = 'none';
        this.tooltip.style.pointerEvents = 'none';
        this.modal.style.pointerEvents = 'auto';

        setTimeout(() => this.modal.classList.add('active'), 50);

        // Bind click events directly to buttons
        document.getElementById('onboarding-cta').addEventListener('click', () => this.nextStep());
        document.getElementById('onboarding-skip').addEventListener('click', () => this.complete());
    }

    showSpotlight(step) {
        const target = document.querySelector(step.target);
        console.log('[Onboarding] showSpotlight:', step.id, 'target:', step.target, 'found:', !!target);
        if (!target) {
            console.log('[Onboarding] Target not found, skipping to next step');
            this.nextStep();
            return;
        }

        target.classList.add('onboarding-highlight');
        target.style.position = target.style.position || 'relative';
        target.style.zIndex = '10001';

        target.scrollIntoView({ behavior: 'smooth', block: 'center' });

        const buildTooltip = (retryCount = 0) => {
            console.log('[Onboarding] buildTooltip running, isActive:', this.isActive, 'currentStep:', this.currentStep, 'expectedStep:', this.steps.indexOf(step), 'retry:', retryCount);
            if (!this.isActive) return;
            if (this.currentStep !== this.steps.indexOf(step)) return;
            
            const rect = target.getBoundingClientRect();
            console.log('[Onboarding] Target rect:', rect.width, rect.height);
            
            if (rect.width === 0 && rect.height === 0) {
                if (retryCount >= 10) { // 最多重试 10 次（1 秒）
                    console.log('[Onboarding] Target remains zero size after retries, forcing next step');
                    this.nextStep();
                    return;
                }
                console.log('[Onboarding] Target has zero size, retrying...');
                setTimeout(() => buildTooltip(retryCount + 1), 100);
                return;
            }
            
            const padding = 8;

            this.spotlight.style.display = 'block';
            this.spotlight.style.left = `${rect.left - padding}px`;
            this.spotlight.style.top = `${rect.top - padding}px`;
            this.spotlight.style.width = `${rect.width + padding * 2}px`;
            this.spotlight.style.height = `${rect.height + padding * 2}px`;

            this.tooltip.className = `onboarding-tooltip position-${step.position || 'right'}`;
            this.tooltip.style.display = '';
            
            let tooltipLeft, tooltipTop;
            const tooltipWidth = 320;

            switch (step.position) {
                case 'right': tooltipLeft = rect.right + 24; tooltipTop = rect.top; break;
                case 'left': tooltipLeft = rect.left - tooltipWidth - 24; tooltipTop = rect.top; break;
                case 'bottom': tooltipLeft = rect.left; tooltipTop = rect.bottom + 24; break;
                case 'top': tooltipLeft = rect.left; tooltipTop = rect.top - 200; break;
                default: tooltipLeft = rect.right + 24; tooltipTop = rect.top;
            }

            tooltipLeft = Math.max(16, Math.min(tooltipLeft, window.innerWidth - tooltipWidth - 16));
            tooltipTop = Math.max(16, Math.min(tooltipTop, window.innerHeight - 250));

            this.tooltip.style.left = `${tooltipLeft}px`;
            this.tooltip.style.top = `${tooltipTop}px`;

            let shortcutsHtml = '';
            if (step.shortcuts) {
                shortcutsHtml = `<div class="tooltip-shortcuts">${step.shortcuts.map(s => `<span class="shortcut-tag">${s}</span>`).join('')}</div>`;
            }

            const isLast = this.currentStep === this.steps.length - 1;
            const isFirst = this.currentStep === 0;

            // Create tooltip content
            let tooltipHtml = `
                <div class="tooltip-header">
                    <span class="tooltip-title">${step.title}</span>
                    <span class="tooltip-step">${this.currentStep + 1}/${this.steps.length}</span>
                </div>
                <p class="tooltip-content">${step.content}</p>
                ${shortcutsHtml}
                <div class="tooltip-actions">
            `;
            
            if (!isFirst) {
                tooltipHtml += '<button class="tooltip-btn-secondary" id="tooltip-prev">上一步</button>';
            }
            
            tooltipHtml += `<button class="tooltip-btn-primary" id="tooltip-next">${isLast ? '完成' : (step.action || '下一步')}</button>`;
            tooltipHtml += `
                </div>
                <div class="tooltip-progress">
                    ${this.steps.map((_, i) => `<span class="progress-dot ${i < this.currentStep ? 'completed' : (i === this.currentStep ? 'active' : '')}"></span>`).join('')}
                </div>
            `;

            this.tooltip.innerHTML = tooltipHtml;

            // Bind click events directly to buttons
            const nextBtn = document.getElementById('tooltip-next');
            const prevBtn = document.getElementById('tooltip-prev');
            
            console.log('[Onboarding] Binding buttons:', { nextBtn: !!nextBtn, prevBtn: !!prevBtn, currentStep: this.currentStep, isLast });
            
            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    console.log('[Onboarding] Next clicked, currentStep:', this.currentStep, 'isLast:', isLast);
                    if (isLast) {
                        this.complete();
                    } else {
                        this.nextStep();
                    }
                });
            }
            
            if (prevBtn) {
                prevBtn.addEventListener('click', () => {
                    console.log('[Onboarding] Prev clicked');
                    this.prevStep();
                });
            }

            setTimeout(() => this.tooltip.classList.add('active'), 50);
        };

        this._tooltipTimeout = setTimeout(buildTooltip, 200);
    }

    updateStepIndicator() {
        this.stepIndicator.innerHTML = `
            <span class="step-indicator-text">步骤 <strong>${this.currentStep + 1}</strong> / ${this.steps.length}</span>
            <button class="step-indicator-skip" id="indicator-skip">跳过</button>
        `;
        this.stepIndicator.classList.add('active');
        document.getElementById('indicator-skip').addEventListener('click', () => this.complete());
    }

    nextStep() { 
        console.log('[Onboarding] nextStep called, currentStep:', this.currentStep);
        this.showStep(this.currentStep + 1); 
    }
    prevStep() { if (this.currentStep > 0) this.showStep(this.currentStep - 1); }

    complete() {
        console.log('[Onboarding] complete() called, isActive:', this.isActive);
        if (!this.isActive) return;
        this.isActive = false;
        
        // Remove keyboard handler
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
            this._keyHandler = null;
        }
        
        // Clear any pending tooltip build timeout
        if (this._tooltipTimeout) {
            clearTimeout(this._tooltipTimeout);
            this._tooltipTimeout = null;
        }
        
        // Clear highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
            el.style.zIndex = '';
        });
        
        // Hide all onboarding elements and disable pointer events
        if (this.overlay) {
            this.overlay.classList.remove('active');
            this.overlay.style.display = 'none';
            this.overlay.style.pointerEvents = 'none';
        }
        if (this.tooltip) {
            this.tooltip.classList.remove('active');
            this.tooltip.style.display = 'none';
            this.tooltip.style.pointerEvents = 'none';
        }
        if (this.modal) {
            this.modal.classList.remove('active');
            this.modal.style.display = 'none';
            this.modal.style.pointerEvents = 'none';
        }
        if (this.spotlight) {
            this.spotlight.style.display = 'none';
        }
        if (this.stepIndicator) {
            this.stepIndicator.classList.remove('active');
            this.stepIndicator.style.display = 'none';
            this.stepIndicator.style.pointerEvents = 'none';
        }
        
        // Mark as completed
        localStorage.setItem(this.storageKey, 'true');
        
        // Clean up all elements after animation
        setTimeout(() => this.cleanupExistingElements(), 100);
    }

    isCompleted() {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    reset() {
        localStorage.removeItem(this.storageKey);
    }

    restart() {
        this.reset();
        this.cleanupExistingElements();
        this.createStyles();
        this.createOverlay();
        this.start();
    }

    destroy() {
        this.cleanupExistingElements();
    }
}

// Helper function to init onboarding for any page
function initOnboarding(page) {
    const onboarding = new Onboarding(page);
    onboarding.init();
    
    // Help shortcut - press ? to restart
    document.addEventListener('keydown', (e) => {
        if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                onboarding.restart();
            }
        }
    });
    
    return onboarding;
}

window.Onboarding = Onboarding;
window.initOnboarding = initOnboarding;
