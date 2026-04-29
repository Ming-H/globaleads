import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, message, Popconfirm, Space, Tag, Descriptions, Card, Typography } from 'antd';
import { ArrowLeftOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { socialTaskService } from '../../services/socialTaskService';
import { socialLeadService } from '../../services/socialLeadService';
import StatusTag from '../../components/StatusTag';
import ScoreBar from '../../components/ScoreBar';
import PlatformIcon from '../../components/PlatformIcon';
import type { SocialTask } from '../../types/socialTask';
import type { SocialLead, SocialLeadStatus } from '../../types/socialLead';

const { Paragraph, Text } = Typography;

const statusOptions = [
  { label: '未联系', value: 'uncontacted' },
  { label: '已联系', value: 'contacted' },
  { label: '已回复', value: 'replied' },
  { label: '无效', value: 'invalid' },
];

export default function SocialTaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>();
  const [task, setTask] = useState<SocialTask | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTask = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const data = await socialTaskService.getTask(Number(id));
        setTask(data);
      } catch {
        message.error('加载任务信息失败');
      } finally {
        setLoading(false);
      }
    };
    fetchTask();
  }, [id]);

  const handleStatusChange = async (leadId: number, status: SocialLeadStatus) => {
    try {
      await socialLeadService.updateStatus(leadId, status);
      message.success('状态已更新');
      actionRef.current?.reload();
    } catch {
      message.error('更新失败');
    }
  };

  const handleStopTask = async () => {
    if (!id) return;
    try {
      await socialTaskService.stopTask(Number(id));
      message.success('任务已停止');
      const updated = await socialTaskService.getTask(Number(id));
      setTask(updated);
      actionRef.current?.reload();
    } catch {
      message.error('操作失败');
    }
  };

  const handleRetryTask = async () => {
    if (!id) return;
    try {
      await socialTaskService.retryTask(Number(id));
      message.success('任务已重新开始');
      const updated = await socialTaskService.getTask(Number(id));
      setTask(updated);
      actionRef.current?.reload();
    } catch {
      message.error('操作失败');
    }
  };

  const columns: ProColumns<SocialLead>[] = [
    {
      title: '平台',
      dataIndex: 'platform',
      width: 100,
      render: (_, record) => <PlatformIcon platform={record.platform} />,
    },
    {
      title: '作者',
      dataIndex: 'author_name',
      width: 120,
      render: (_, record) => (
        <a href={record.author_url} target="_blank" rel="noreferrer">
          {record.author_name}
        </a>
      ),
    },
    {
      title: '内容摘要',
      dataIndex: 'content',
      ellipsis: true,
      search: false,
    },
    {
      title: '意向评分',
      dataIndex: 'ai_score',
      width: 150,
      sorter: true,
      render: (_, record) => <ScoreBar score={record.ai_score} />,
    },
    {
      title: '标签',
      dataIndex: 'ai_tags',
      width: 180,
      search: false,
      render: (_, record) => (
        <Space wrap>
          {record.ai_tags?.map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
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
      title: '发布时间',
      dataIndex: 'published_at',
      valueType: 'dateTime',
      width: 180,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {record.post_url && (
            <Button
              type="link"
              size="small"
              href={record.post_url}
              target="_blank"
            >
              查看原帖
            </Button>
          )}
          <select
            style={{ width: 100, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: '4px' }}
            value={record.status}
            onChange={(e) => handleStatusChange(record.id, e.target.value as SocialLeadStatus)}
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
        onClick={() => navigate('/social-tasks')}
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
          <Descriptions.Item label="关键词">
            <Space wrap>
              {task.keywords.map((kw) => (
                <Tag key={kw}>{kw}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="平台">
            <Space wrap>
              {task.platforms.map((p) => (
                <PlatformIcon key={p} platform={p} />
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="线索数">{task.lead_count}</Descriptions.Item>
          <Descriptions.Item label="最大结果数">{task.max_results}</Descriptions.Item>
          <Descriptions.Item label="最低评分">{task.min_score}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(task.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <ProTable<SocialLead>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        headerTitle="任务线索列表"
        search={{
          labelWidth: 'auto',
          filterType: 'light',
        }}
        request={async (params) => {
          const result = await socialLeadService.getLeads({
            page: params.current || 1,
            page_size: params.pageSize || 20,
            task_id: Number(id),
            status: params.status as SocialLeadStatus | undefined,
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
        scroll={{ x: 1200 }}
      />
    </div>
  );
}
