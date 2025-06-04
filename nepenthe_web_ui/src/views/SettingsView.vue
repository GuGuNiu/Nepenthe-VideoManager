<template>
  <div class="settings-view-container">
    <el-tabs v-model="activeOuterTab" tab-position="left" class="settings-main-tabs">
      <el-tab-pane label="应用配置" name="appConfig" class="settings-tab-pane">
        <el-form :model="currentSettings" label-width="120px" label-position="left" ref="settingsFormRef">
          <h2>应用配置</h2>
          <el-tabs v-model="activeInnerConfigTab" class="inner-config-tabs">
            <el-tab-pane label="后端服务" name="backendService">
              <el-form-item label="API 主机">
                <el-input v-model="currentSettings.apiHost" placeholder="例如: 127.0.0.1"></el-input>
              </el-form-item>
              <el-form-item label="API 端口">
                <el-input-number v-model="currentSettings.apiPort" :min="1024" :max="65535" placeholder="例如: 8000"></el-input-number>
              </el-form-item>
              <el-form-item label="FFmpeg 路径">
                <el-input v-model="currentSettings.ffmpegPath" placeholder="FFmpeg 可执行文件完整路径">
                  <template #append>
                    <el-button :icon="FolderIcon" @click="browseExecutable('ffmpegPath')"></el-button>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="FFprobe 路径">
                <el-input v-model="currentSettings.ffprobePath" placeholder="FFprobe 可执行文件完整路径">
                  <template #append>
                    <el-button :icon="FolderIcon" @click="browseExecutable('ffprobePath')"></el-button>
                  </template>
                </el-input>
              </el-form-item>
              <el-alert title="提示" type="info" show-icon :closable="false" style="margin-bottom: 15px;">
                修改API主机/端口或FFmpeg/FFprobe路径后，点击页面底部的"保存所有设置"以生效。
              </el-alert>
            </el-tab-pane>

            <el-tab-pane label="视频库操作" name="videoLibraryOps" class="settings-tab-pane">
              <div class="video-library-ops-container">
                <div class="video-paths-management-section">
                  <h3>视频库路径管理</h3>
                  <el-alert type="info" show-icon :closable="false" style="margin-top: 15px;margin-bottom: 15px;">
                    视频库路径的添加和删除会尝试立即更新后端配置并清理数据。最终的路径列表也需要通过页面底部的"保存所有设置"按钮进行持久化。
                  </el-alert>
                  <div class="add-path-controls">
                    <span>添加新的视频库路径:</span>
                    <el-button type="primary" plain @click="addVideoPath" :icon="PlusIcon" size="small">选择文件夹</el-button>
                  </div>
                  <div class="video-paths-list-scrollable" v-if="currentSettings.videoPaths.length > 0">
                    <div v-for="(path, index) in currentSettings.videoPaths" :key="index" class="path-item-card">
                      <span class="path-text-display" :title="path">{{ path }}</span>
                      <el-button type="danger" :icon="DeleteIcon" circle size="small" @click="removeVideoPath(index)" class="path-remove-btn-card"></el-button>
                    </div>
                  </div>
                  <el-empty description="暂未添加视频库路径" v-else style="margin-top: 10px; padding: 10px 0;"></el-empty>
                </div>

                <div class="library-scan-section">
                  <h3>数据库与扫描</h3>
                  <div class="scan-action-area">
                      <el-button 
                          type="primary" 
                          @click="triggerScanLibrary" 
                          :loading="isScanning" 
                          :icon="RefreshRightIcon" 
                          class="scan-button"
                          size="large" 
                      >
                          {{ isScanning ? '扫描中...' : '扫描/更新视频库' }}
                      </el-button>
                  </div>
                  <div class="scan-info-area"> 
                      <div class="scan-info-item">上次扫描: {{ libraryStats.last_scan_time ? formatScanTime(libraryStats.last_scan_time) : '从未' }}</div>
                      <div class="scan-info-item">视频数量: {{ libraryStats.total_videos }}</div>
                      <div class="scan-info-item" v-if="libraryStats.total_size_bytes !== null">总容量: {{ formatBytes(libraryStats.total_size_bytes) }}</div>
                      <div class="scan-info-item" v-else>总容量: 计算中或未知</div>
                      <el-button 
                          @click="fetchLibraryStats" 
                          :icon="RefreshLeftIcon" 
                          size="small" 
                          :loading="isFetchingStats"
                          style="margin-top: 10px;"
                          plain
                        >
                          刷新统计
                        </el-button>
                  </div>
                  <el-alert v-if="scanMessage" :title="scanMessage.text" :type="scanMessage.type" show-icon :closable="false" style="margin-top:15px;" />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
          
          <div class="form-actions">
            <el-button type="primary" @click="saveAllSettings" :loading="isSaving" size="large">保存所有设置</el-button>
            <el-button @click="loadSettings" size="large">重置为上次加载的值</el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="前端日志" name="frontendLog" class="settings-tab-pane log-pane">
        <div class="log-viewer">
          <div class="log-header">
            <span>前端渲染进程日志</span>
            <el-button size="small" @click="clearFrontendLogs" type="info" plain>清空日志</el-button>
          </div>
          <pre class="log-content" ref="frontendLogContentRef">{{ frontendLogs.join('\n') }}</pre>
        </div>
      </el-tab-pane>

      <el-tab-pane label="关于" name="about" class="settings-tab-pane">
        <div class="about-section">
          <h2>关于 Nepenthe 视频管理</h2>
          <p>版本: {{ appVersion }}</p>
          <p>仓库地址: 
            <a href="https://github.com/GuGuNiu/Nepenthe-VideoManager" target="_blank" @click.prevent="openExternalLink('https://github.com/GuGuNiu/Nepenthe-VideoManager')">
              https://github.com/GuGuNiu/Nepenthe-VideoManager
            </a>
          </p>
          <p>© {{ new Date().getFullYear() }} GuGuNiu. All Rights Reserved.</p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch, inject } from 'vue';
import { ElMessage } from 'element-plus';
import { 
    Delete as DeleteIcon, 
    Plus as PlusIcon, 
    Folder as FolderIcon, 
    RefreshRight as RefreshRightIcon, 
    RefreshLeft as RefreshLeftIcon,
} from '@element-plus/icons-vue';
import axios from 'axios';
import { API_BASE_URL, isConfigLoaded as appConfigIsLoaded } from '../services/appConfigService'; 
import { format } from 'date-fns';

const currentSettings = reactive({
  apiHost: '', apiPort: 8000, videoPaths: [], ffmpegPath: '', ffprobePath: '',
});
const isSaving = ref(false);
const activeOuterTab = ref('appConfig'); 
const activeInnerConfigTab = ref('backendService'); 

const frontendLogs = inject('globalFrontendLogs', ref([])); 
const clearFrontendLogsInjected = inject('clearGlobalFrontendLogs', () => {
  console.warn('[SettingsView] clearGlobalFrontendLogs function was not provided.');
});
const frontendLogContentRef = ref(null); 

const clearFrontendLogs = () => { 
  clearFrontendLogsInjected(); 
};

watch(frontendLogs, () => { 
  nextTick(() => { 
    if (frontendLogContentRef.value) {
        frontendLogContentRef.value.scrollTop = 0; 
    }
  }); 
}, { deep: true, immediate: false });

const appVersion = ref('0.1.0'); 
const scanMessage = ref(null);
const isFetchingStats = ref(false);
const isScanning = ref(false);
const libraryStats = reactive({ total_videos: 0, total_size_bytes: null, last_scan_time: null });
const settingsFormRef = ref(null);

let previousVideoPathsForDirtyCheck = [];

const loadSettings = async () => { 
    if (window.electronApp?.getAppConfig) { 
        try { 
            const s = await window.electronApp.getAppConfig(); 
            if (s) { 
                currentSettings.apiHost = s.apiHost || ''; 
                currentSettings.apiPort = s.apiPort || 8000; 
                currentSettings.videoPaths = Array.isArray(s.videoPaths) ? [...s.videoPaths] : []; 
                currentSettings.ffmpegPath = s.ffmpegPath || ''; 
                currentSettings.ffprobePath = s.ffprobePath || ''; 
                previousVideoPathsForDirtyCheck = [...currentSettings.videoPaths]; 
            }
        } catch (e) { ElMessage.error('Failed to load settings.'); console.error('[SettingsView] Error loading settings:', e); }
    } else { ElMessage.warning('Cannot access configuration interface.'); }
};

const saveAllSettings = async () => { 
    if (!window.electronApp?.setConfigKey) {
        ElMessage.error('Cannot access configuration interface to save.'); 
        return;
    }
    isSaving.value = true; 
    try { 
        await window.electronApp.setConfigKey('apiHost', currentSettings.apiHost); 
        await window.electronApp.setConfigKey('apiPort', Number(currentSettings.apiPort)); 
        
        const newVideoPaths = [...currentSettings.videoPaths];
        await window.electronApp.setConfigKey('videoPaths', newVideoPaths); 
        
        await window.electronApp.setConfigKey('ffmpegPath', currentSettings.ffmpegPath); 
        await window.electronApp.setConfigKey('ffprobePath', currentSettings.ffprobePath); 
        
        ElMessage.success('所有设置已保存！'); 
        console.info('[SettingsView] All settings saved to store.');

        const pathsEffectivelyChanged = JSON.stringify(previousVideoPathsForDirtyCheck.slice().sort()) !== JSON.stringify(newVideoPaths.slice().sort());
        
        if (pathsEffectivelyChanged) {
            if (API_BASE_URL.value) {
                try {
                    console.info('[SettingsView] Video paths changed upon saving all, triggering sync/cleanup.');
                    await axios.post(`${API_BASE_URL.value}/api/library/sync-and-clean`, {
                        current_paths: newVideoPaths 
                    });
                    previousVideoPathsForDirtyCheck = [...newVideoPaths]; 
                    setTimeout(() => fetchLibraryStats(), 2000);
                } catch (syncError) {
                    ElMessage.error(syncError.response?.data?.detail || 'Failed to trigger library sync/cleanup task after saving all settings.');
                    console.error('[SettingsView] Error triggering library sync-and-clean post-save:', syncError);
                }
            } else {
                ElMessage.error('API address not configured, cannot trigger sync/cleanup for path changes.');
            }
        }
    } catch (e) { 
        ElMessage.error('Failed to save some settings.'); 
        console.error('[SettingsView] Error saving settings via IPC:', e);
    } finally { 
        isSaving.value = false; 
    }
};

const addVideoPath = async () => { 
    if (!window.electronApp?.browseDirectory) {
        ElMessage.info('Folder selection feature is unavailable.');
        return;
    }
    const p = await window.electronApp.browseDirectory(); 
    if (p && !currentSettings.videoPaths.includes(p)) {
        currentSettings.videoPaths.push(p);
        ElMessage.success(`路径 "${p}" 已添加到当前列表。请记得点击“保存所有设置”以永久保存。`);
        // 路径添加后，不立即保存到 store，也不立即触发后端清理。
        // 用户需要点击底部的“保存所有设置”来确认这些更改。
        // 扫描时会使用当前列表中的路径。
    }
};

const removeVideoPath = async (index) => { 
    const removedPath = currentSettings.videoPaths.splice(index, 1)[0];
    ElMessage.info(`路径 "${removedPath}" 已从当前列表中移除。此更改将在下次扫描或保存时生效。`);
    
    // 当路径从UI列表移除时，立即调用后端清理，使用移除后的路径列表
    // 这是为了即时清理数据，即使主 "Save All Settings" 还没点
    if (API_BASE_URL.value) {
        console.info(`[SettingsView] Path removed from UI, triggering immediate sync-and-clean with current paths:`, [...currentSettings.videoPaths]);
        try {
            await axios.post(`${API_BASE_URL.value}/api/library/sync-and-clean`, {
                current_paths: [...currentSettings.videoPaths] 
            });
            console.info('[SettingsView] Immediate library sync-and-clean triggered successfully.');
            setTimeout(() => fetchLibraryStats(), 2000);
        } catch (error) {
            ElMessage.error('Failed to trigger immediate cleanup task for removed path.');
            console.error('[SettingsView] Error triggering immediate sync-and-clean for removed path:', error);
        }
    } else {
        ElMessage.warning('API address not configured, cannot trigger immediate cleanup for removed path.');
    }
};

const triggerScanLibrary = async () => { 
    if (!API_BASE_URL.value) { ElMessage.error('API address not configured.'); return; } 
    isScanning.value = true; 
    scanMessage.value = { text: '视频库扫描任务已在后台启动...', type: 'info' }; 
    ElMessage.success('视频库扫描任务已在后台启动...');
    const pathsToScanNow = [...currentSettings.videoPaths];
    console.info('[SettingsView] Triggering library scan. Paths being sent:', pathsToScanNow); 
    try { 
        await axios.post(`${API_BASE_URL.value}/api/scan-library`, { 
            paths_to_scan: pathsToScanNow 
        }); 
        setTimeout(() => { fetchLibraryStats(); }, 10000); 
    } catch (error) { 
        ElMessage.error(error.response?.data?.detail || 'Failed to start scan.'); 
        scanMessage.value = { text: 'Failed to start scan.', type: 'error' }; 
        console.error('[SettingsView] Error triggering library scan:', error); 
    } finally { 
        isScanning.value = false; 
    }
};

const formatScanTime = (ds) => { if(!ds)return 'Never'; try{return format(new Date(ds),'yyyy/MM/dd HH:mm:ss');}catch(e){return String(ds);}};
const formatBytes = (b,d=2)=>{if(b===null||b===undefined||!Number.isFinite(b)||b<0)return'0 B';if(b===0)return'0 B';const k=1024,m=d<0?0:d,s=['Bytes','KB','MB','GB','TB'];const i=Math.floor(Math.log(b)/Math.log(k));return`${parseFloat((b/Math.pow(k,i)).toFixed(m))} ${s[i]}`;};
const fetchLibraryStats = async () => { if (!API_BASE_URL.value) { ElMessage.error('API address not configured.'); isFetchingStats.value = false; return; } isFetchingStats.value = true; scanMessage.value = null; try { const response = await axios.get(`${API_BASE_URL.value}/api/library/stats`); if (response.data) { libraryStats.total_videos = response.data.total_videos || 0; libraryStats.total_size_bytes = response.data.total_size_bytes; libraryStats.last_scan_time = response.data.last_scan_time; }} catch (error) { ElMessage.error(error.response?.data?.detail || 'Failed to get library stats.');} finally { isFetchingStats.value = false; }};
const browseExecutable = async (key) => { if (window.electronApp?.browseFile && window.electronApp?.getPlatform) { const pf = await window.electronApp.getPlatform(); const f = (key==='ffmpegPath'||key==='ffprobePath')?(pf==='win32'?[{name:'Executable',extensions:['exe']}]:[{name:'All Files',extensions:['*']}]):[{name:'All Files',extensions:['*']}]; const fp = await window.electronApp.browseFile({title:`Select ${key==='ffmpegPath'?'FFmpeg':'FFprobe'}`,filters:f}); if(fp)currentSettings[key]=fp;}else{ElMessage.info('File selection feature is unavailable.'); }};
const openExternalLink = (urlToOpen) => { if(window.electronApp?.openExternal){window.electronApp.openExternal(urlToOpen);}else{window.open(urlToOpen,'_blank');}};

onMounted(() => {
  let unwatchConfigLoaded = null;
  unwatchConfigLoaded = watch(appConfigIsLoaded, (loaded) => {
    if (loaded) {
      loadSettings(); 
      if (API_BASE_URL.value && API_BASE_URL.value !== '') {
        fetchLibraryStats(); 
      } else {
        ElMessage.warning('API base URL is not available, cannot fetch library stats.');
      }
      if (window.electronApp?.getAppVersion) {
        window.electronApp.getAppVersion().then(v => { if(v) appVersion.value = v; });
      }
      if (unwatchConfigLoaded) unwatchConfigLoaded();
    }
  }, { immediate: true });
});

onBeforeUnmount(() => {
});
</script>

<style scoped>
.settings-view-container { padding: 20px; height: calc(100vh - 120px); display: flex; flex-direction: column; }
.settings-main-tabs { flex-grow: 1; display: flex; }
.settings-main-tabs :deep(.el-tabs__content) { height: 100%; overflow-y: auto; padding-left: 20px; }
.settings-tab-pane { height: 100%; display: flex; flex-direction: column; }
.el-form { flex-grow: 1; overflow-y: auto; padding-right: 15px; paddingTop: 10px; padding-bottom: 20px; }
.inner-config-tabs { margin-bottom: 20px; }

.video-library-ops-container {
  display: flex;
  gap: 20px; 
  height: 100%; 
}
.video-paths-management-section {
  flex: 1; 
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  min-width: 300px;
}
.library-scan-section {
  flex: 1;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  min-width: 300px;
}
.video-paths-management-section h3,
.library-scan-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #303133;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
}

.add-path-controls { display: flex; align-items: center; margin-bottom: 15px; }
.add-path-controls span { font-size: 14px; color: #606266; margin-right: 10px; }
.video-paths-list-scrollable {
  flex-grow: 1;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  min-height: 100px; 
  max-height: 300px;
}
.path-item-card { 
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  padding: 6px 8px; 
  border-bottom: 1px solid #f0f0f0; 
  font-size: 13px; 
  overflow: hidden; 
  background-color: #fdfdff; 
  border-left: 3px solid var(--el-color-primary-light-5); 
  margin-bottom: 4px; 
  border-radius: 3px;
}
.path-item-card:last-child {
  border-bottom: none;
  margin-bottom: 0;
}
.path-text-display { 
  flex-grow: 1; 
  white-space: nowrap; 
  overflow: hidden; 
  text-overflow: ellipsis; 
  margin-right: 8px; 
  cursor: default; 
}
.path-remove-btn-card { flex-shrink: 0; }

.scan-action-area { text-align: center; margin-bottom: 20px; }
.scan-button { width: 100%; max-width: 800px; }
.scan-info-area { padding: 15px; border: 1px solid #ebeef5; border-radius: 4px; background-color: #f9f9f9; }
.scan-info-item { margin: 6px 0; font-size: 14px; color: #606266; }

.el-form-item { margin-bottom: 22px; }
.form-actions { margin-top: 30px; display: flex; gap: 10px; justify-content: flex-end; }

.log-pane { display: flex; flex-direction: column; flex-grow: 1; }
.log-viewer { display: flex; flex-direction: column; flex-grow: 1; border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; }
.log-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background-color: #f5f7fa; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.log-header span { font-weight: bold; }
.log-content { flex-grow: 1; overflow-y: auto; padding: 10px; white-space: pre-wrap; word-break: break-all; font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace; font-size: 12px; line-height: 1.5; background-color: #ffffff; }

.about-section { line-height: 1.8; }
.about-section h2 { margin-bottom: 15px; }
.about-section p { margin-bottom: 10px; }
.about-section a { color: var(--el-color-primary); text-decoration: none; }
.about-section a:hover { text-decoration: underline; }
</style>