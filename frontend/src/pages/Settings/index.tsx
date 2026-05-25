import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Input,
  Button,
  message,
  Row,
  Col,
  Statistic,
  Divider,
  Space,
} from 'antd';
import {
  RobotOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { settingsService } from '../../services/settingsService';
import type { AIConfig } from '../../services/settingsService';

const providerOptions = [
  { label: 'Ollama (本地)', value: 'ollama' },
  { label: 'DeepSeek (云端)', value: 'deepseek' },
];

const modelOptions: Record<string, { label: string; value: string }[]> = {
  ollama: [
    { label: 'qwen3:0.6b', value: 'qwen3:0.6b' },
    { label: 'qwen3:1.7b', value: 'qwen3:1.7b' },
    { label: 'qwen3:4b', value: 'qwen3:4b' },
    { label: 'llama3:8b', value: 'llama3:8b' },
  ],
  deepseek: [
    { label: 'deepseek-chat', value: 'deepseek-chat' },
    { label: 'deepseek-reasoner', value: 'deepseek-reasoner' },
  ],
};

const apiNameMap: Record<string, string> = {
  reddit: 'Reddit',
  bluesky: 'Bluesky',
  youtube: 'YouTube',
  google_search: 'Google Search',
  osm: 'OpenStreetMap',
};

export default function Settings() {
  const [form] = Form.useForm();
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [apiUsage, setApiUsage] = useState<Record<string, { used: number; limit: number | string }>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const selectedProvider = Form.useWatch('provider', form);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [configData, usageData] = await Promise.all([
        settingsService.getAIConfig(),
        settingsService.getApiUsage(),
      ]);
      setConfig(configData);
      setApiUsage(usageData);
      form.setFieldsValue(configData);
    } catch {
      message.error('获取设置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: AIConfig) => {
    setSaving(true);
    try {
      const updated = await settingsService.updateAIConfig(values);
      setConfig(updated);
      message.success('配置已保存');
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>AI 模型配置</span>
          </Space>
        }
        loading={loading}
        style={{ marginBottom: 24 }}
      >
        {config && (
          <div style={{ marginBottom: 16, color: '#666' }}>
            当前配置: {config.provider === 'ollama' ? 'Ollama' : 'DeepSeek'} ({config.model})
          </div>
        )}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          style={{ maxWidth: 500 }}
        >
          <Form.Item
            label="提供商"
            name="provider"
            rules={[{ required: true, message: '请选择提供商' }]}
          >
            <Select options={providerOptions} placeholder="选择AI提供商" />
          </Form.Item>

          <Form.Item
            label="模型"
            name="model"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select
              options={modelOptions[selectedProvider] || []}
              placeholder="选择模型"
            />
          </Form.Item>

          <Form.Item label="API Key" name="api_key">
            <Input.Password placeholder="可选，DeepSeek需要填写" />
          </Form.Item>

          <Form.Item label="Base URL" name="base_url">
            <Input placeholder="可选，自定义服务地址" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存配置
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={
          <Space>
            <ApiOutlined />
            <span>API 额度</span>
          </Space>
        }
        loading={loading}
      >
        <Row gutter={[16, 16]}>
          {Object.entries(apiUsage).map(([key, info]) => (
            <Col xs={24} sm={12} lg={8} key={key}>
              <Card size="small" bordered>
                <Statistic
                  title={apiNameMap[key] || key}
                  value={info.used}
                  suffix={
                    typeof info.limit === 'number'
                      ? `/ ${info.limit}`
                      : `(${info.limit})`
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
}
