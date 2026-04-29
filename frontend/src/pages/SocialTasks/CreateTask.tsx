import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Space,
  message,
  Tag,
} from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import { socialTaskService } from '../../services/socialTaskService';

const platformOptions = [
  { label: 'Reddit', value: 'reddit' },
  { label: 'Bluesky', value: 'bluesky' },
  { label: 'YouTube', value: 'youtube' },
];

export default function CreateSocialTask() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState('');

  const addKeyword = () => {
    const trimmed = keywordInput.trim();
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
      setKeywordInput('');
    }
  };

  const removeKeyword = (kw: string) => {
    setKeywords(keywords.filter((k) => k !== kw));
  };

  const handleSubmit = async (values: {
    name: string;
    platforms: string[];
    max_results?: number;
    min_score?: number;
  }) => {
    if (keywords.length === 0) {
      message.warning('请至少添加一个关键词');
      return;
    }
    setLoading(true);
    try {
      await socialTaskService.createTask({
        name: values.name,
        keywords,
        platforms: values.platforms,
        max_results: values.max_results || 100,
        min_score: values.min_score || 0,
      });
      message.success('任务创建成功');
      navigate('/social-tasks');
    } catch {
      message.error('创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Card title="创建社媒挖掘任务" style={{ maxWidth: 700 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            platforms: ['reddit'],
            max_results: 100,
            min_score: 60,
          }}
        >
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：LED灯具Reddit挖掘" />
          </Form.Item>

          <Form.Item label="关键词" required>
            <Space wrap style={{ marginBottom: 8 }}>
              {keywords.map((kw) => (
                <Tag
                  key={kw}
                  closable
                  onClose={() => removeKeyword(kw)}
                  closeIcon={<CloseOutlined />}
                  color="blue"
                >
                  {kw}
                </Tag>
              ))}
            </Space>
            <Input
              placeholder="输入关键词后按回车或点击添加"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onPressEnter={(e) => {
                e.preventDefault();
                addKeyword();
              }}
              addonAfter={
                <PlusOutlined
                  onClick={addKeyword}
                  style={{ cursor: 'pointer' }}
                />
              }
            />
          </Form.Item>

          <Form.Item
            label="目标平台"
            name="platforms"
            rules={[{ required: true, message: '请选择至少一个平台' }]}
          >
            <Select
              mode="multiple"
              options={platformOptions}
              placeholder="选择目标平台"
            />
          </Form.Item>

          <Form.Item label="最大采集数" name="max_results">
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="最低意向评分" name="min_score">
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button onClick={() => navigate('/social-tasks')}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                开始挖掘
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
