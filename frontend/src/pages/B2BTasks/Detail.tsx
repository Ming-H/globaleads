import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, message, Popconfirm, Space, Tag, Descriptions, Card } from 'antd';
import { ArrowLeftOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { b2bTaskService } from '../../services/b2bTaskService';
import { b2bLeadService } from '../../services/b2bLeadService';
import StatusTag from '../../components/StatusTag';
import PlatformIcon from '../../components/PlatformIcon';
import type { B2BTask } from '../../types/b2bTask';
import type { B2BLead, B2BLeadStatus } from '../../types/b2bLead';

const statusOptions = [
  { label: '未联系', value: 'uncontacted' },
  { label: '已联系', value: 'contacted' },
  { label: '已回复', value: 'replied' },
  { label: '无效', value: 'invalid' },
];

export default function B2BTaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>();
  const [task, setTask] = useState<B2BTask | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTask = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const data = await b2bTaskService.getTask(Number(id));
        setTask(data);
      } catch {
        message.error('加载任务信息失败');
      } finally {
        setLoading(false);
      }
    };
    fetchTask();
  }, [id]);

  const handleStatusChange = async (leadId: number, status: B2BLeadStatus) => {
    try {
      await b2bLeadService.updateStatus(leadId, status);
      message.success('状态已更新');
      actionRef.current?.reload();
    } catch {
      message.error('更新失败');
    }
  };

  const handleStopTask = async () => {
    if (!id) return;
    try {
      await b2bTaskService.stopTask(Number(id));
      message.success('任务已停止');
      const updated = await b2bTaskService.getTask(Number(id));
      setTask(updated);
      actionRef.current?.reload();
    } catch {
      message.error('操作失败');
    }
  };

  const handleRetryTask = async () => {
    if (!id) return;
    try {
      await b2bTaskService.retryTask(Number(id));
      message.success('任务已重新开始');
      const updated = await b2bTaskService.getTask(Number(id));
      setTask(updated);
      actionRef.current?.reload();
    } catch {
      message.error('操作失败');
    }
  };

  const columns: ProColumns<B2BLead>[] = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      width: 200,
      render: (_, record) =>
        record.company_website ? (
          <a href={record.company_website} target="_blank" rel="noreferrer">
            {record.company_name}
          </a>
        ) : (
          record.company_name
        ),
    },
    {
      title: '联系人',
      dataIndex: 'contact_name',
      width: 120,
      search: false,
    },
    {
      title: '邮箱',
      dataIndex: 'contact_email',
      width: 200,
      search: false,
      render: (_, record) =>
        record.contact_email ? (
          <a href={`mailto:${record.contact_email}`}>{record.contact_email}</a>
        ) : (
          <Tag>无邮箱</Tag>
        ),
    },
    {
      title: '行业',
      dataIndex: 'industry',
      width: 120,
    },
    {
      title: '地区',
      dataIndex: 'region',
      width: 140,
    },
    {
      title: '数据源',
      dataIndex: 'data_source',
      width: 120,
      render: (_, record) => <PlatformIcon platform={record.data_source} />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        uncontacted: { text: '未联系', status: 'Default' },
        contacted: { text: '已联系', status: 'Processing' },
        replied: { text: '已回复', status: 'Success' },
        invalid: { text: '无效', status: 'Error' },
      },
      render: (_, record) => <StatusTag status={record.status} />,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {record.company_website && (
            <Button
              type="link"
              size="small"
              href={record.company_website}
              target="_blank"
            >
              访问网站
            </Button>
          )}
          <select
            style={{ width: 100, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: '4px' }}
            value={record.status}
            onChange={(e) => handleStatusChange(record.id, e.target.value as B2BLeadStatus)}
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </Space>
      ),
    },
  ];

  if (loading || !task) {
    return <div>加载中...</div>;
  }

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/b2b-tasks')}
        style={{ marginBottom: 16 }}
      >
        返回任务列表
      </Button>

      <Card
        title={task.name}
        extra={
          <Space>
            {task.status === 'running' && (
              <Popconfirm
                title="确定要停止该任务吗？"
                onConfirm={handleStopTask}
              >
                <Button danger icon={<StopOutlined />}>
                  停止任务
                </Button>
              </Popconfirm>
            )}
            {task.status === 'failed' && (
              <Popconfirm
                title="确定要重试该任务吗？"
                onConfirm={handleRetryTask}
              >
                <Button icon={<ReloadOutlined />}>
                  重试任务
                </Button>
              </Popconfirm>
            )}
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions column={2} bordered>
          <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusTag status={task.status} />
          </Descriptions.Item>
          <Descriptions.Item label="行业">{task.industry}</Descriptions.Item>
          <Descriptions.Item label="地区">{task.region}</Descriptions.Item>
          <Descriptions.Item label="公司规模">{task.company_size || '不限'}</Descriptions.Item>
          <Descriptions.Item label="数据源">
            <Space wrap>
              {task.data_sources.map((s) => (
                <PlatformIcon key={s} platform={s} />
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="线索数">{task.lead_count}</Descriptions.Item>
          <Descriptions.Item label="最大结果数">{task.max_results}</Descriptions.Item>
          <Descriptions.Item label="创建时间" span={2}>
            {new Date(task.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <ProTable<B2BLead>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        headerTitle="任务线索列表"
        search={{
          labelWidth: 'auto',
          filterType: 'light',
        }}
        request={async (params) => {
          const result = await b2bLeadService.getLeads({
            page: params.current || 1,
            page_size: params.pageSize || 20,
            task_id: Number(id),
            status: params.status as B2BLeadStatus | undefined,
          });
          return {
            data: result.items,
            total: result.total,
            success: true,
          };
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        scroll={{ x: 1300 }}
      />
    </div>
  );
}
