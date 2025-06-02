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
                修改API主机/端口或FFmpeg/FFprobe路径后，你可能需要重启后端服务才能完全生效。
              </el-alert>
            </el-tab-pane>

            <el-tab-pane label="视频库管理" name="videoLibrary">
              <div class="add-path-controls">
                <span>添加新的视频库路径:</span>
                <el-button type="primary" plain @click="addVideoPath" :icon="PlusIcon" size="small">选择文件夹</el-button>
              </div>
              <div class="video-paths-list" v-if="currentSettings.videoPaths.length > 0">
                <div v-for="(path, index) in currentSettings.videoPaths" :key="index" class="path-item-card">
                  <span class="path-text-display" :title="path">{{ path }}</span>
                  <el-button type="danger" :icon="DeleteIcon" circle size="small" @click="removeVideoPath(index)" class="path-remove-btn-card"></el-button>
                </div>
              </div>
              <el-empty description="暂未添加视频库路径" v-else style="margin-top: 20px;"></el-empty>
            </el-tab-pane>
            
            <el-tab-pane label="数据库与扫描" name="databaseScan" class="settings-tab-pane">
              <div class="scan-section-wrapper"> 
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
              </div>
              <el-alert v-if="scanMessage" :title="scanMessage.text" :type="scanMessage.type" show-icon :closable="false" style="margin-top:15px;" />
          </el-tab-pane>
          </el-tabs>
          
          <div class="form-actions">
            <el-button type="primary" @click="saveAllSettings" :loading="isSaving" size="large">保存所有设置</el-button>
            <el-button @click="loadSettings" size="large">重置为上次保存的值</el-button>
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

      <el-tab-pane label="后端日志" name="backendLog" class="settings-tab-pane log-pane">
         <div class="log-viewer">
          <div class="log-header">
            <span>后端服务运行日志</span>
            <el-button size="small" @click="clearBackendLogs" type="info" plain>清空日志</el-button>
          </div>
          <pre class="log-content" ref="backendLogContentRef">{{ backendLogs.join('\n') }}</pre>
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
    Refresh as RefreshIcon,
    Search as SearchIcon 
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
const clearFrontendLogsInjected = inject('clearGlobalFrontendLogs', () => {});
const frontendLogContentRef = ref(null); 
const backendLogs = ref([]); 
const backendLogContentRef = ref(null);
let cleanupBackendLogListener = null;

const MAX_LOG_LINES = 500; 
const TRIM_LOG_LINES_TO = 400;

const appVersion = ref('0.1.0'); 
const scanMessage = ref(null);
const isFetchingStats = ref(false);
const isScanning = ref(false);
const libraryStats = reactive({ total_videos: 0, total_size_bytes: null, last_scan_time: null });

const clearFrontendLogs = () => { clearFrontendLogsInjected(); };
const clearBackendLogs = () => { backendLogs.value = []; };

watch(frontendLogs, () => { nextTick(() => { if (frontendLogContentRef.value) frontendLogContentRef.value.scrollTop = 0; }); }, { deep: true });
watch(backendLogs, () => { nextTick(() => { if (backendLogContentRef.value) backendLogContentRef.value.scrollTop = backendLogContentRef.value.scrollHeight; }); }, { deep: true });

const loadSettings = async () => { if (window.electronApp?.getAppConfig) { try { const s = await window.electronApp.getAppConfig(); if (s) { currentSettings.apiHost = s.apiHost || '127.0.0.1'; currentSettings.apiPort = s.apiPort || 8000; currentSettings.videoPaths = Array.isArray(s.videoPaths) ? [...s.videoPaths] : []; currentSettings.ffmpegPath = s.ffmpegPath || ''; currentSettings.ffprobePath = s.ffprobePath || ''; }} catch (e) { ElMessage.error('加载配置失败。'); }} else { ElMessage.warning('无法访问配置接口。');}};
const saveAllSettings = async () => { if (window.electronApp?.setConfigKey) { isSaving.value = true; try { await window.electronApp.setConfigKey('apiHost', currentSettings.apiHost); await window.electronApp.setConfigKey('apiPort', Number(currentSettings.apiPort)); await window.electronApp.setConfigKey('videoPaths', [...currentSettings.videoPaths]); await window.electronApp.setConfigKey('ffmpegPath', currentSettings.ffmpegPath); await window.electronApp.setConfigKey('ffprobePath', currentSettings.ffprobePath); ElMessage.success('设置已保存！部分更改可能需重启后端生效。'); } catch (e) { ElMessage.error('保存设置失败。'); } finally { isSaving.value = false; }} else { ElMessage.error('无法访问配置接口。');}};
const addVideoPath = async () => { if (window.electronApp?.browseDirectory) { const p = await window.electronApp.browseDirectory(); if (p && !currentSettings.videoPaths.includes(p)) currentSettings.videoPaths.push(p); } else { ElMessage.info('文件夹选择功能不可用。'); }};
const removeVideoPath = (index) => { currentSettings.videoPaths.splice(index, 1); };
const browseExecutable = async (key) => { if (window.electronApp?.browseFile && window.electronApp?.getPlatform) { const pf = await window.electronApp.getPlatform(); const f = (key==='ffmpegPath'||key==='ffprobePath')?(pf==='win32'?[{name:'可执行文件',extensions:['exe']}]:[{name:'所有文件',extensions:['*']}]):[{name:'所有文件',extensions:['*']}]; const fp = await window.electronApp.browseFile({title:`选择${key==='ffmpegPath'?'FFmpeg':'FFprobe'}`,filters:f}); if(fp)currentSettings[key]=fp;}else{ElMessage.info('文件选择功能不可用。');}};
const formatScanTime = (ds) => { if(!ds)return '从未'; try{return format(new Date(ds),'yyyy/MM/dd HH:mm:ss');}catch(e){return String(ds);}};
const formatBytes = (b,d=2)=>{if(b===null||b===undefined||!Number.isFinite(b)||b<0)return'0 B';if(b===0)return'0 B';const k=1024,m=d<0?0:d,s=['Bytes','KB','MB','GB','TB'];const i=Math.floor(Math.log(b)/Math.log(k));return`${parseFloat((b/Math.pow(k,i)).toFixed(m))} ${s[i]}`;};
const fetchLibraryStats = async () => { if (!API_BASE_URL.value) { ElMessage.error('API地址未配置。'); isFetchingStats.value = false; return; } isFetchingStats.value = true; scanMessage.value = null; try { const response = await axios.get(`${API_BASE_URL.value}/api/library/stats`); if (response.data) { libraryStats.total_videos = response.data.total_videos || 0; libraryStats.total_size_bytes = response.data.total_size_bytes; libraryStats.last_scan_time = response.data.last_scan_time; }} catch (error) { ElMessage.error(error.response?.data?.detail || '获取库统计失败。');} finally { isFetchingStats.value = false; }};
const triggerScanLibrary = async () => { if (!API_BASE_URL.value) { ElMessage.error('API地址未配置。'); return; } isScanning.value = true; scanMessage.value = { text: '视频库扫描任务已在后台启动...', type: 'info' }; ElMessage.info('视频库扫描任务已在后台启动，请稍候...'); try { await axios.post(`${API_BASE_URL.value}/api/scan-library`); setTimeout(() => { fetchLibraryStats(); }, 5000); } catch (error) { ElMessage.error(error.response?.data?.detail || '启动扫描失败。'); scanMessage.value = { text: '启动扫描失败。', type: 'error' }; } finally { isScanning.value = false; }};
const openExternalLink = (urlToOpen) => { if(window.electronApp?.openExternal){window.electronApp.openExternal(urlToOpen);}else{window.open(urlToOpen,'_blank');}};

onMounted(() => {
  let unwatchConf = null;
  unwatchConf = watch(appConfigIsLoaded, (loaded) => {
    if (loaded) {
      loadSettings(); 
      if (API_BASE_URL.value) fetchLibraryStats(); 
      else ElMessage.warning('API配置未完全加载，统计功能可能不可用。');
      if (window.electronApp?.getAppVersion) window.electronApp.getAppVersion().then(v => { if(v)appVersion.value = v; });
      if (unwatchConf) unwatchConf();
    }
  }, { immediate: true });
  if (window.electronApp?.onBackendLogMessage) {
    cleanupBackendLogListener = window.electronApp.onBackendLogMessage((message) => {
      backendLogs.value.push(message);
      if (backendLogs.value.length > MAX_LOG_LINES) backendLogs.value.splice(0, backendLogs.value.length - TRIM_LOG_LINES_TO);
      nextTick(() => { if (backendLogContentRef.value) backendLogContentRef.value.scrollTop = backendLogContentRef.value.scrollHeight; });
    });
  }
});
onBeforeUnmount(() => {
  if (cleanupBackendLogListener) { cleanupBackendLogListener(); cleanupBackendLogListener = null; }
});
</script>

<style scoped>
.settings-view-container { padding: 20px; height: calc(100vh - 120px); display: flex; flex-direction: column; }
.settings-main-tabs { flex-grow: 1; display: flex; }
.settings-main-tabs :deep(.el-tabs__content) { height: 100%; overflow-y: auto; padding-left: 20px; }
.settings-tab-pane { height: 100%; display: flex; flex-direction: column; }
.el-form { flex-grow: 1; overflow-y: auto; padding-right: 15px; paddingTop: 10px; padding-bottom: 20px; }
.inner-config-tabs { margin-bottom: 20px; }
.media-tools-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #ebeef5; }
.media-tools-header h3 { margin-top: 0; margin-bottom: 0; line-height: 32px; font-size: 16px; color: #303133; }
.scan-section-wrapper { display: flex; flex-direction: column; gap: 20px; }
.scan-action-area { text-align: center; }
.scan-button { width: 80%; max-width: 300px; }
.scan-info-area { padding: 15px; border: 1px solid #ebeef5; border-radius: 4px; background-color: #f9f9f9; }
.scan-info-item { margin: 6px 0; font-size: 14px; color: #606266; }

.video-paths-list { margin-bottom: 10px; max-height: 150px; overflow-y: auto; border: 1px solid #dcdfe6; border-radius: 4px; padding: 5px; }
.add-path-controls { display: flex; align-items: center; margin-bottom: 15px; }
.add-path-controls span { font-size: 14px; color: #606266; margin-right: 10px; }
.video-paths-grid { /* This class was in your template, but not in your provided CSS. Adding a basic grid. */
  display: grid; 
  grid-template-columns: 1fr; /* Default to one column, can be changed if needed */
  gap: 10px; 
  margin-top: 10px; 
}
.path-item-card { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 4px; background-color: #fff; font-size: 13px; overflow: hidden; }
.path-text-display { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 8px; cursor: default; }
.path-remove-btn-card { flex-shrink: 0; }
.el-form-item { margin-bottom: 22px; }
.form-actions { margin-top: 30px; display: flex; gap: 10px; justify-content: flex-end; }

.log-pane { display: flex; flex-direction: column; flex-grow: 1; }
.log-viewer { display: flex; flex-direction: column; flex-grow: 1; border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; }
.log-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background-color: #f5f7fa; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.log-header span { font-weight: bold; }
.log-content { flex-grow: 1; overflow-y: auto; padding: 10px; white-space: pre-wrap; word-break: break-all; font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace; font-size: 12px; line-height: 1.5; background-color: #ffffff; }
.log-content pre { margin: 0; }

.about-section { line-height: 1.8; }
.about-section h2 { margin-bottom: 15px; }
.about-section p { margin-bottom: 10px; }
.about-section a { color: var(--el-color-primary); text-decoration: none; }
.about-section a:hover { text-decoration: underline; }
</style>