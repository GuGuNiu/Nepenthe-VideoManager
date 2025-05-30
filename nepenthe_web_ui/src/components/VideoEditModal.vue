<template>
  <el-dialog
    :model-value="visible"
    title="编辑视频信息"
    width="700px"
    @update:modelValue="$emit('update:visible', $event)"
    @closed="resetFormOnClose"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form :model="editableVideo" label-width="80px" ref="editFormRef" v-if="editableVideo.id !== null">
      <el-form-item label="视频名称：" prop="name">
        <el-input v-model="editableVideo.name" placeholder="请输入视频名称"></el-input>
      </el-form-item>
      
      <el-form-item label="标签：" prop="tags_edit">
        <div class="tag-edit-area">
          <el-tag
            v-for="tag in editableVideo.tags_edit" :key="tag" closable
            @close="handleTagRemove(tag)" style="margin-right: 5px; margin-bottom: 5px;"
          >
            {{ tag }}
          </el-tag>
          <el-input
            v-if="tagInputVisible"
            v-model="tagInputValue"
            ref="tagInputRef"
            size="small"
            @keyup.enter="handleTagInputConfirm"
            @blur="handleTagInputConfirm"
            placeholder="按回车添加标签"
            class="input-new-tag"
          />
          <el-button v-else size="small" @click="showTagInput" class="button-new-tag">
            + 新增标签
          </el-button>
        </div>
      </el-form-item>
      
      <el-form-item label="人物" prop="persons_edit">
        <div class="tag-edit-area">
          <el-tag
            v-for="person in editableVideo.persons_edit" :key="person" closable
            @close="handlePersonRemove(person)" type="warning"
            style="margin-right: 5px; margin-bottom: 5px;"
          >
            {{ person }}
          </el-tag>
          <el-input
            v-if="personInputVisible"
            v-model="personInputValue"
            ref="personInputRef"
            size="small"
            @keyup.enter="handlePersonInputConfirm"
            @blur="handlePersonInputConfirm"
            placeholder="按回车添加人物"
            class="input-new-tag"
          />
          <el-button v-else size="small" @click="showPersonInput" class="button-new-tag">
            + 新增人物
          </el-button>
        </div>
      </el-form-item>
      
      <el-form-item label="精选评级：" prop="rating">
        <el-rate v-model="editableVideo.rating" :max="5" allow-half clearable />
      </el-form-item>

      <el-form-item label="文件路径：" prop="path" v-if="editableVideo.path">
        <div class="path-display-area">
          <span class="video-path-text" :title="editableVideo.path">{{ editableVideo.path }}</span>
          <el-button 
            size="small" 
            @click="openVideoFolder" 
            class="open-folder-button" 
            :icon="FolderOpenedIcon"
          >
            打开文件夹
          </el-button>
        </div>
      </el-form-item>
    </el-form>
    <div v-else>
      加载中...
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="isSubmitting">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, nextTick, reactive } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { FolderOpened as FolderOpenedIcon } from '@element-plus/icons-vue';

const props = defineProps({ visible: Boolean, videoData: Object });
const emit = defineEmits(['update:visible', 'video-updated']);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const editableVideo = reactive({ 
  id: null, 
  name: '', 
  tags_edit: [], 
  persons_edit: [], 
  rating: 0,
  path: '' 
});
const editFormRef = ref(null);
const isSubmitting = ref(false);
const tagInputVisible = ref(false);
const tagInputValue = ref('');
const tagInputRef = ref(null);
const personInputVisible = ref(false);
const personInputValue = ref('');
const personInputRef = ref(null);

const resetEditableVideo = () => {
  editableVideo.id = null; 
  editableVideo.name = ''; 
  editableVideo.tags_edit = []; 
  editableVideo.persons_edit = []; 
  editableVideo.rating = 0;
  editableVideo.path = '';
};

const resetFormOnClose = () => {
  if (editFormRef.value) {
    editFormRef.value.resetFields(); // 重置表单校验状态等
  }
  resetEditableVideo(); // 调用已定义的函数
  tagInputVisible.value = false; 
  tagInputValue.value = '';
  personInputVisible.value = false; 
  personInputValue.value = '';
};


watch(() => props.videoData, (newData) => {
  if (newData && typeof newData === 'object') { // 确保 newData 是一个对象    
    editableVideo.id = newData.id !== undefined ? newData.id : null;
    editableVideo.name = newData.name || '';
    editableVideo.tags_edit = newData.tags ? newData.tags.map(tag => typeof tag === 'object' ? tag.name : tag) : [];
    editableVideo.persons_edit = newData.persons ? newData.persons.map(p => typeof p === 'object' ? p.name : p) : [];
    editableVideo.rating = newData.rating !== null && newData.rating !== undefined ? newData.rating : 0;
    
    if (newData.path !== undefined) { 
        editableVideo.path = String(newData.path); // 强制转换为字符串
    } else {
        editableVideo.path = '';
    }
  } else {
    resetEditableVideo();
  }
}, { immediate: true, deep: true });

const handleTagRemove = (tagToRemove) => { editableVideo.tags_edit = editableVideo.tags_edit.filter(tag => tag !== tagToRemove); };
const showTagInput = () => { tagInputVisible.value = true; nextTick(() => { tagInputRef.value?.input?.focus(); }); };
const handleTagInputConfirm = () => { const newTag = tagInputValue.value.trim(); if (newTag && !editableVideo.tags_edit.includes(newTag)) editableVideo.tags_edit.push(newTag); tagInputVisible.value = false; tagInputValue.value = ''; };
const handlePersonRemove = (personToRemove) => { editableVideo.persons_edit = editableVideo.persons_edit.filter(p => p !== personToRemove); };
const showPersonInput = () => { personInputVisible.value = true; nextTick(() => { personInputRef.value?.input?.focus(); }); };
const handlePersonInputConfirm = () => { const newPerson = personInputValue.value.trim(); if (newPerson && !editableVideo.persons_edit.includes(newPerson)) editableVideo.persons_edit.push(newPerson); personInputVisible.value = false; personInputValue.value = ''; };
const openVideoFolder = () => {
  if (editableVideo.path) {
    if (window.electronAPI && typeof window.electronAPI.showItemInFolder === 'function') {
      window.electronAPI.showItemInFolder(editableVideo.path);
    } else {
      ElMessage.warning('无法调用本地文件管理器功能 (electronAPI.showItemInFolder 未找到)。');
      navigator.clipboard.writeText(editableVideo.path).then(() => {
        ElMessage.success('路径已复制到剪贴板');
      }).catch(err => {
        ElMessage.error('复制路径失败');
      });
    }
  } else {
    ElMessage.warning('视频路径为空，无法打开文件夹。');
  }
};
const submitForm = async () => {
  if (!editableVideo.id) { ElMessage.error('无效的视频数据'); return; }
  isSubmitting.value = true;
  try {
    const payload = { 
      name: editableVideo.name, 
      tags: editableVideo.tags_edit, 
      persons: editableVideo.persons_edit, 
      rating: editableVideo.rating 
    };
    const response = await axios.put(`${API_BASE_URL}/api/videos/${editableVideo.id}`, payload);
    emit('video-updated', response.data);
    emit('update:visible', false);
  } catch (error) {
    console.error('更新视频失败:', error.response || error);
    ElMessage.error(error.response?.data?.detail || '更新视频失败，请检查网络或联系管理员。');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.tag-edit-area { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.input-new-tag { width: 120px; }
.dialog-footer { text-align: right; }
.path-display-area {
  display: flex;
  align-items: center;
  width: 100%;
}
.video-path-text {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 10px;
  font-size: 13px;
  color: #606266;
  cursor: default;
}
.open-folder-button {
  flex-shrink: 0;
}
</style>