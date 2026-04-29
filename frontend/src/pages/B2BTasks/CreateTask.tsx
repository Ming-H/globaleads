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
} from 'antd';
import { b2bTaskService } from '../../services/b2bTaskService';

const industryOptions = [
  { label: '照明 (Lighting)', value: 'Lighting' },
  { label: '电子 (Electronics)', value: 'Electronics' },
  { label: '制造 (Manufacturing)', value: 'Manufacturing' },
  { label: '建材 (Building Materials)', value: 'Building Materials' },
  { label: '家居 (Home & Garden)', value: 'Home & Garden' },
  { label: '服装 (Apparel)', value: 'Apparel' },
  { label: '汽配 (Automotive)', value: 'Automotive' },
  { label: '其他 (Other)', value: 'Other' },
];

const regionOptions = [
  { label: '美国 (United States)', value: 'United States' },
  { label: '英国 (United Kingdom)', value: 'United Kingdom' },
  { label: '德国 (Germany)', value: 'Germany' },
  { label: '法国 (France)', value: 'France' },
  { label: '加拿大 (Canada)', value: 'Canada' },
  { label: '澳大利亚 (Australia)', value: 'Australia' },
  { label: '日本 (Japan)', value: 'Japan' },
  { label: '其他 (Other)', value: 'Other' },
];

const dataSourceOptions = [
  { label: 'Apollo', value: 'apollo' },
  { label: 'Google Maps', value: 'google_maps' },
];

const companySizeOptions = [
  { label: '不限', value: '' },
  { label: '1-10人', value: '1-10' },
  { label: '11-50人', value: '11-50' },
  { label: '51-200人', value: '51-200' },
  { label: '201-500人', value: '201-500' },
  { label: '501-1000人', value: '501-1000' },
  { label: '1000人以上', value: '1000+' },
];

export default function CreateB2BTask() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: {
    name: string;
    industry: string;
    region: string;
    company_size?: string;
    data_sources: string[];
    max_results?: number;
  }) => {
    setLoading(true);
    try {
      await b2bTaskService.createTask({
        name: values.name,
        industry: values.industry,
        region: values.region,
        company_size: values.company_size || undefined,
        data_sources: values.data_sources,
        max_results: values.max_results || 100,
      });
      message.success('任务创建成功');
      navigate('/b2b-tasks');
    } catch {
      message.error('创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Card title="创建B2B搜索任务" style={{ maxWidth: 700 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            data_sources: ['apollo'],
            max_results: 100,
          }}
        >
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：美国LED经销商搜索" />
          </Form.Item>

          <Form.Item
            label="行业"
            name="industry"
            rules={[{ required: true, message: '请选择行业' }]}
          >
            <Select
              options={industryOptions}
              placeholder="选择目标行业"
              showSearch
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="目标地区"
            name="region"
            rules={[{ required: true, message: '请选择地区' }]}
          >
            <Select
              options={regionOptions}
              placeholder="选择目标地区"
              showSearch
              allowClear
            />
          </Form.Item>

          <Form.Item label="公司规模" name="company_size">
            <Select
              options={companySizeOptions}
              placeholder="选择公司规模"
              allowClear
            />
          </Form.Item>

          <Form.Item
            label="数据源"
            name="data_sources"
            rules={[{ required: true, message: '请选择至少一个数据源' }]}
          >
            <Select
              mode="multiple"
              options={dataSourceOptions}
              placeholder="选择数据来源"
            />
          </Form.Item>

          <Form.Item label="最大采集数" name="max_results">
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button onClick={() => navigate('/b2b-tasks')}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                开始搜索
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
