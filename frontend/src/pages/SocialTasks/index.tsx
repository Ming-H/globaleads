import { useRef } from 'react';
import { Button, message, Popconfirm, Space, Tag } from 'antd';
import { PlusOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { useNavigate } from 'react-router-dom';
import { socialTaskService } from '../../services/socialTaskService';
import StatusTag from '../../components/StatusTag';
import PlatformIcon from '../../components/PlatformIcon';
import type { SocialTask } from '../../types/socialTask';

export default function SocialTasks() {
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();

  const columns: ProColumns<SocialTask>[] = [
    {
      title: '任务名称',
      dataIndex: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      width: 200,
      search: false,
      render: (_, record) => (
        <Space wrap>
          {record.keywords.map((kw) => (
            <Tag key={kw}>{kw}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '平台',
      dataIndex: 'platforms',
      width: 200,
      search: false,
      render: (_, record) => (
        <Space wrap>
          {record.platforms.map((p) => (
            <PlatformIcon key={p} platform={p} />
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        pending: { text: '等待中', status: 'Default' },
        running: { text: '运行中', status: 'Processing' },
        completed: { text: '已完成', status: 'Success' },
        failed: { text: '失败', status: 'Error' },
      },
      render: (_, record) => <StatusTag status={record.status} />,
    },
    {
      title: '线索数',
      dataIndex: 'lead_count',
      width: 80,
      search: false,
      sorter: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      width: 180,
      search: false,
      sorter: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/social-tasks/${record.id}`)}
          >
            查看详情
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/social-leads?task_id=${record.id}`)}
          >
            查看线索
          </Button>
          {record.status === 'running' && (
            <Popconfirm
              title="确定要停止该任务吗？"
              onConfirm={async () => {
                try {
                  await socialTaskService.stopTask(record.id);
                  message.success('任务已停止');
                  actionRef.current?.reload();
                } catch {
                  message.error('操作失败');
                }
              }}
            >
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                停止
              </Button>
            </Popconfirm>
          )}
          {record.status === 'failed' && (
            <Popconfirm
              title="确定要重试该任务吗？"
              onConfirm={async () => {
                try {
                  await socialTaskService.retryTask(record.id);
                  message.success('任务已重新开始');
                  actionRef.current?.reload();
                } catch {
                  message.error('操作失败');
                }
              }}
            >
              <Button type="link" size="small" icon={<ReloadOutlined />}>
                重试
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <ProTable<SocialTask>
      columns={columns}
      actionRef={actionRef}
      rowKey="id"
      headerTitle="社媒挖掘任务"
      toolBarRender={() => [
        <Button
          key="create"
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/social-tasks/create')}
        >
          创建任务
        </Button>,
      ]}
      request={async (params) => {
        const result = await socialTaskService.getTasks({
          page: params.current || 1,
          page_size: params.pageSize || 20,
          status: params.status,
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
      scroll={{ x: 1100 }}
      search={{
        labelWidth: 'auto',
        filterType: 'light',
      }}
    />
  );
}
