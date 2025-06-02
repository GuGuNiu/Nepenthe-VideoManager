import { ref, readonly } from 'vue';

const internalApiBaseUrl = ref('');
const internalConfigLoaded = ref(false);
const internalAllStoredConfigs = ref(null); // 重命名以区分导出的 ref
const internalIsPackagedMode = ref(false);
const internalAppDataDir = ref('');
const allConfigsFromMain = ref(null);

async function loadAppConfig() {
    if (window.electronApp && typeof window.electronApp.getAppConfig === 'function') {
        try {
            const config = await window.electronApp.getAppConfig();
            allConfigsFromMain.value = config;
            if (config && config.apiHost && config.apiPort) {
                internalApiBaseUrl.value = `http://${config.apiHost}:${config.apiPort}`;
            } else {
                internalApiBaseUrl.value = 'http://127.0.0.1:28000'; // 最终回退
                console.error('[AppConfigService] Invalid config from main or apiHost/Port missing.');
            }
        } catch (error) {
            internalApiBaseUrl.value = 'http://127.0.0.1:28000'; // 出错时的回退
            console.error('[AppConfigService] Error fetching config from main:', error);
        }
    } else {
        internalApiBaseUrl.value = 'http://127.0.0.1:8000'; // 极特殊情况的回退 (例如preload失败)
        console.warn('[AppConfigService] electronApp.getAppConfig not found. Using hardcoded default.');
    }
    internalConfigLoaded.value = true;
    console.log('[AppConfigService] API Base URL set to:', internalApiBaseUrl.value);
}

loadAppConfig();

export const API_BASE_URL = readonly(internalApiBaseUrl);
export const isConfigLoaded = readonly(internalConfigLoaded);
export const storedConfigs = readonly(internalAllStoredConfigs); // 直接导出响应式 ref (只读)
export const isPackagedMode = readonly(internalIsPackagedMode);
export const appDataDir = readonly(internalAppDataDir);

export async function reloadAppConfig() {
    internalConfigLoaded.value = false;
    internalAllStoredConfigs.value = null; 
    internalApiBaseUrl.value = ''; 
    internalIsPackagedMode.value = false;
    internalAppDataDir.value = '';
    await loadAppConfig();
}